#include <Python.h>
#include <dirent.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <limits.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/syscall.h>

struct linux_dirent64 {
	uint64_t        d_ino;
	int64_t         d_off;
	unsigned short  d_reclen;
	unsigned char   d_type;
	char            d_name[];
};

struct getdents_state {
	PyObject_HEAD
	char  *buff;
	int    bpos;
	int    fd;
	int    nread;
	size_t buff_size;
#ifdef Py_GIL_DISABLED
	PyMutex lock;
#endif
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

#ifdef Py_GIL_DISABLED
# define LOCK(s) PyMutex_Lock(&(s)->lock);
# define UNLOCK(s) PyMutex_Unlock(&(s)->lock);
#else
# define LOCK(s)
# define UNLOCK(s)
#endif

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

static PyObject *
getdents_new(PyTypeObject *type, PyObject *args, PyObject *Py_UNUSED(kwargs))
{
	size_t buff_size;
	int fd;

	if (!PyArg_ParseTuple(args, "in", &fd, &buff_size)) {
		return NULL;
	}

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

	struct getdents_state *state = (void *) tp_alloc(type, 0);

	if (!state) {
		return NULL;
	}

	void *buff = PyMem_Malloc(buff_size);

	if (!buff) {
		Py_DECREF(state);
		return PyErr_NoMemory();
	}

	state->buff = buff;
	state->buff_size = buff_size;
	state->fd = fd;
	state->bpos = 0;
	state->nread = 0;

#ifdef Py_GIL_DISABLED
	state->lock = (PyMutex){0};
#endif

	return (PyObject *) state;
}

static void
getdents_dealloc(struct getdents_state *state)
{
	PyTypeObject *tp = Py_TYPE(state);
	freefunc tp_free = PyType_GetSlot(tp, Py_tp_free);

	assert(tp_free != NULL);

	if (state->buff) {
		PyMem_Free(state->buff);
	}

	tp_free(state);
	Py_DECREF(tp);
}

static PyObject *
getdents_next(struct getdents_state *self)
{
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

	UNLOCK(self);

	return dirent64_to_python(dirent);
}

static PyObject *
getdents_call(struct getdents_state *self, PyObject *Py_UNUSED(args), PyObject *Py_UNUSED(kwargs))
{
	LOCK(self);

	if (!has_next(self)) {
		_refill(self);

		switch (self->nread) {
		case 0:
			UNLOCK(self);
			return Py_None;
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

static PyType_Slot getdents_type_slots[] = {
	{Py_tp_alloc, PyType_GenericAlloc},
	{Py_tp_dealloc, getdents_dealloc},
	{Py_tp_iter, PyObject_SelfIter},
	{Py_tp_iternext, getdents_next},
	{Py_tp_new, getdents_new},
	{Py_tp_call, getdents_call},
	{0, 0},
};

static PyType_Spec getdents_type_spec = {
	.name = "getdents.getdents_raw",
	.basicsize = sizeof(struct getdents_state),
	.flags = Py_TPFLAGS_DEFAULT,
	.slots = getdents_type_slots,
};

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
