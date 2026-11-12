#include <Python.h>
#include <dirent.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdbool.h>
#include <limits.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>

// Relative offsets for __vectorcalloffset__ require Python 3.14.
// See: https://docs.python.org/3.14/c-api/structures.html#c.PyMemberDef
#if (defined(Py_TARGET_ABI3T) && Py_TARGET_ABI3T+0 >= 0x030e0000) || \
    (defined(Py_LIMITED_API) && Py_LIMITED_API+0 >= 0x030e0000) || \
    (!defined(Py_TARGET_ABI3T) && !defined(Py_LIMITED_API) && PY_VERSION_HEX >= 0x030e0000)
# define GETDENTS_VECTORCALL 1
#endif

struct linux_dirent64 {
	uint64_t        d_ino;
	int64_t         d_off;
	unsigned short  d_reclen;
	unsigned char   d_type;
	char            d_name[];
};

struct getdents_state {
#ifdef GETDENTS_VECTORCALL
	vectorcallfunc vectorcall;
#endif
	char  *buff;
	int    bpos;
	int    fd;
	int    nread;
	size_t buff_size;
	PyThread_type_lock lock;
};

#ifndef O_GETDENTS
# define O_GETDENTS (O_DIRECTORY | O_RDONLY | O_NONBLOCK | O_CLOEXEC)
#endif

#ifndef MIN_GETDENTS_BUFF_SIZE
# ifdef NAME_MAX
#  define MIN_GETDENTS_BUFF_SIZE (NAME_MAX + sizeof(struct linux_dirent64))
# else
#  define MIN_GETDENTS_BUFF_SIZE (MAXNAMLEN + sizeof(struct linux_dirent64))
# endif
#endif

static inline void lock_state(struct getdents_state *state) {
	Py_BEGIN_ALLOW_THREADS
	PyThread_acquire_lock(state->lock, WAIT_LOCK);
	Py_END_ALLOW_THREADS
}

#define LOCK(s) lock_state(s)
#define UNLOCK(s) PyThread_release_lock((s)->lock)

static inline struct getdents_state *getdents_get_state(PyObject *object) {
	PyTypeObject *type = (PyTypeObject *)PyObject_Type(object);

	if (!type) {
		return NULL;
	}

	struct getdents_state *state = PyObject_GetTypeData(object, type);
	Py_DECREF(type);
	return state;
}

static inline bool has_next(struct getdents_state *self) {
	return self->bpos < self->nread;
}

static inline int _count(struct getdents_state *self) {
	struct linux_dirent64 *d;
	int bpos = self->bpos;
	int count = 0;

	while (bpos < self->nread) {
		d = (void *)(self->buff + bpos);
		bpos += d->d_reclen;
		count++;
	}

	return count;
}

static inline struct linux_dirent64 *_next(struct getdents_state *self) {
	struct linux_dirent64 *dirent = (void *)(self->buff + self->bpos);
	self->bpos += dirent->d_reclen;
	return dirent;
}

static inline void _refill(struct getdents_state *self) {
	self->bpos = 0;
	Py_BEGIN_ALLOW_THREADS
	self->nread = syscall(
		SYS_getdents64,
		self->fd,
		self->buff,
		self->buff_size
	);
	Py_END_ALLOW_THREADS
}

static PyObject *
dirent64_to_python(struct linux_dirent64 *d)
{
	assert(d != NULL);

	PyObject *py_name = PyUnicode_DecodeFSDefaultAndSize(
		d->d_name,
		strnlen(
			d->d_name,
			d->d_reclen - offsetof(struct linux_dirent64, d_name)
		)
	);

	if (!py_name) {
		return NULL;
	}

	return Py_BuildValue("KbO", d->d_ino, d->d_type, py_name);
}

static int getdents_exec(PyObject *module);

#ifdef Py_tp_vectorcall
static PyObject *
getdents_new_vectorcall(
	PyObject *type,
	PyObject *const *args,
	size_t nargsf,
	PyObject *Py_UNUSED(kwnames)
)
{
	int fd;
	Py_ssize_t buff_size;
	Py_ssize_t nargs = PyVectorcall_NARGS(nargsf);

	if (nargs != 2) {
		PyErr_Format(
			PyExc_TypeError,
			"getdents_raw() takes exactly 2 arguments (%zd given)",
			nargs
		);

		return NULL;
	}

	if (!PyArg_Parse(args[0], "i", &fd) || !PyArg_Parse(args[1], "n", &buff_size)) {
		return NULL;
	}

	return _getdents_new((PyTypeObject *)type, fd, buff_size);
}
#endif

static PyObject *
getdents_new(PyTypeObject *type, PyObject *args, PyObject *Py_UNUSED(kwargs))
{
	Py_ssize_t buff_size;
	int fd;

	if (!PyArg_ParseTuple(args, "in", &fd, &buff_size)) {
		return NULL;
	}

	return _getdents_new(type, fd, buff_size);
}

static PyObject *
_getdents_new(PyTypeObject *type, int fd, Py_ssize_t buff_size)
{
	if (!(fcntl(fd, F_GETFL) & O_DIRECTORY)) {
		PyErr_SetString(
			PyExc_NotADirectoryError,
			"fd must be opened with O_DIRECTORY flag"
		);
		return NULL;
	}

	if (buff_size < MIN_GETDENTS_BUFF_SIZE) {
		PyErr_SetString(
			PyExc_ValueError,
			"buff_size is too small"
		);
		return NULL;
	}

	allocfunc tp_alloc = PyType_GetSlot(type, Py_tp_alloc);

	assert(tp_alloc != NULL);

	PyObject *object = tp_alloc(type, 0);

	if (!object) {
		return NULL;
	}

	struct getdents_state *state = PyObject_GetTypeData(object, type);

#ifdef GETDENTS_VECTORCALL
	state->vectorcall = getdents_vectorcall;
#endif
	state->buff = NULL;
	state->buff_size = buff_size;
	state->fd = fd;
	state->bpos = 0;
	state->nread = 0;
	state->lock = PyThread_allocate_lock();

	if (!state->lock) {
		Py_DECREF(object);
		return PyErr_NoMemory();
	}

	void *buff = PyMem_Malloc(buff_size);

	if (!buff) {
		Py_DECREF(object);
		return PyErr_NoMemory();
	}

	state->buff = buff;

	return object;
}

static void
getdents_dealloc(PyObject *object)
{
	PyObject *type_object = PyObject_Type(object);

	if (!type_object) {
		Py_FatalError("failed to get getdents_raw type during deallocation");
	}

	PyTypeObject *tp = (PyTypeObject *)type_object;
	struct getdents_state *state = PyObject_GetTypeData(object, tp);

	if (!state) {
		Py_FatalError("failed to get getdents_raw state during deallocation");
	}

	freefunc tp_free = PyType_GetSlot(tp, Py_tp_free);

	assert(tp_free != NULL);

	if (state->buff) {
		PyMem_Free(state->buff);
	}

	if (state->lock) {
		PyThread_free_lock(state->lock);
	}

	tp_free(object);
	Py_DECREF(type_object);
	Py_DECREF(tp);
}

static PyObject *
getdents_next(PyObject *object)
{
	struct getdents_state *self = getdents_get_state(object);

	if (!self) {
		return NULL;
	}

	LOCK(self);

	if (!has_next(self)) {
		_refill(self);

		switch (self->nread) {
		case 0:
			UNLOCK(self);
			return NULL;
		case -1:
			UNLOCK(self);
			PyErr_SetString(PyExc_OSError, "getdents64");
			return NULL;
		}
	}

	struct linux_dirent64 *dirent = _next(self);
	PyObject *result = dirent64_to_python(dirent);

	UNLOCK(self);

	return result;
}

static PyObject *
_getdents_call(PyObject *object)
{
	struct getdents_state *self = getdents_get_state(object);

	if (!self) {
		return NULL;
	}

	LOCK(self);

	if (!has_next(self)) {
		_refill(self);

		switch (self->nread) {
		case 0:
			UNLOCK(self);
			Py_RETURN_NONE;
		case -1:
			UNLOCK(self);
			PyErr_SetString(PyExc_OSError, "getdents64");
			return NULL;
		}
	}

	int count = _count(self);
	PyObject *out = PyList_New(count);

	if (!out) {
		UNLOCK(self);
		return NULL;
	}

	for (int i = 0; i < count; i++) {
		PyObject *py_dirent = dirent64_to_python(_next(self));

		if (!py_dirent) {
			Py_DECREF(out);
			UNLOCK(self);
			return NULL;
		}

		if (PyList_SetItem(out, i, py_dirent) < 0) {
			Py_DECREF(py_dirent);
			Py_DECREF(out);
			UNLOCK(self);
			return NULL;
		}
	}

	UNLOCK(self);

	return out;
}

static PyObject *
getdents_call(
	PyObject *object,
	PyObject *Py_UNUSED(args),
	PyObject *Py_UNUSED(kwargs)
)
{
	return _getdents_call(object);
}

static PyObject *
getdents_vectorcall(
	PyObject *object,
	PyObject *const *Py_UNUSED(args),
	size_t Py_UNUSED(nargsf),
	PyObject *Py_UNUSED(kwnames)
)
{
	return _getdents_call(object);
}

#ifdef GETDENTS_VECTORCALL
static PyMemberDef getdents_members[] = {
	{
		"__vectorcalloffset__",
		Py_T_PYSSIZET,
		offsetof(struct getdents_state, vectorcall),
		Py_READONLY | Py_RELATIVE_OFFSET
	},
	{NULL},
};
#endif

static PyType_Slot getdents_type_slots[] = {
	{Py_tp_alloc, PyType_GenericAlloc},
	{Py_tp_dealloc, getdents_dealloc},
	{Py_tp_iter, PyObject_SelfIter},
	{Py_tp_iternext, getdents_next},
	{Py_tp_new, getdents_new},
	{Py_tp_call, getdents_call},
#ifdef Py_tp_vectorcall
	{Py_tp_vectorcall, getdents_new_vectorcall},
#endif
#ifdef GETDENTS_VECTORCALL
	{Py_tp_members, getdents_members},
#endif
	{0, 0},
};

static PyType_Spec getdents_type_spec = {
	.name = "getdents.getdents_raw",
	.basicsize = -(int)sizeof(struct getdents_state),
#ifdef GETDENTS_VECTORCALL
	.flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_IMMUTABLETYPE | Py_TPFLAGS_HAVE_VECTORCALL,
#else
	.flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_IMMUTABLETYPE,
#endif
	.slots = getdents_type_slots,
};

#if defined(Py_TARGET_ABI3T)
PyABIInfo_VAR(getdents_abi_info);

static PySlot getdents_export_slots[] = {
	PySlot_STATIC_DATA(Py_mod_abi, &getdents_abi_info),
	PySlot_STATIC_DATA(Py_mod_name, "getdents._getdents"),
	PySlot_STATIC_DATA(Py_mod_doc, ""),
	PySlot_SIZE(Py_mod_state_size, 0),
	PySlot_FUNC(Py_mod_exec, getdents_exec),
	PySlot_DATA(Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED),
	PySlot_DATA(Py_mod_gil, Py_MOD_GIL_NOT_USED),
	PySlot_END,
};

PyMODEXPORT_FUNC PyModExport__getdents(void)
{
	return getdents_export_slots;
}
#else
PyModuleDef_Slot getdents_slots[] = {
	{Py_mod_exec, getdents_exec},
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x030c0000
	{Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#endif
#if !defined(Py_LIMITED_API) && defined(Py_GIL_DISABLED)
	{Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
	{0, NULL}
};

static struct PyModuleDef getdents_module = {
	PyModuleDef_HEAD_INIT,
	.m_name = "getdents",
	.m_doc = "",
	.m_size = 0,
	.m_slots = getdents_slots,
};

PyMODINIT_FUNC
PyInit__getdents(void)
{
	return PyModuleDef_Init(&getdents_module);
}
#endif

static int
getdents_exec(PyObject *module)
{
	PyObject *getdents_raw = PyType_FromSpec(&getdents_type_spec);

	if (!getdents_raw) {
		return -1;
	}

	if (PyModule_AddObject(module, "getdents_raw", getdents_raw) < 0) {
		Py_DECREF(getdents_raw);
		return -1;
	}

	PyModule_AddIntMacro(module, DT_BLK);
	PyModule_AddIntMacro(module, DT_CHR);
	PyModule_AddIntMacro(module, DT_DIR);
	PyModule_AddIntMacro(module, DT_FIFO);
	PyModule_AddIntMacro(module, DT_LNK);
	PyModule_AddIntMacro(module, DT_REG);
	PyModule_AddIntMacro(module, DT_SOCK);
	PyModule_AddIntMacro(module, DT_UNKNOWN);
	PyModule_AddIntMacro(module, O_GETDENTS);
	PyModule_AddIntMacro(module, MIN_GETDENTS_BUFF_SIZE);

	return 0;
}
