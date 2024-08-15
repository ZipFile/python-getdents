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

static PyObject *
getdents_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
	size_t buff_size;
	int fd;

	if (!PyArg_ParseTuple(args, "in", &fd, &buff_size))
		return NULL;

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

	if (!state)
		return NULL;

	void *buff = PyMem_Malloc(buff_size);

	if (!buff)
		return PyErr_NoMemory();

	state->buff = buff;
	state->buff_size = buff_size;
	state->fd = fd;
	state->bpos = 0;
	state->nread = 0;
	return (PyObject *) state;
}

static void
getdents_dealloc(struct getdents_state *state)
{
	PyTypeObject *tp = Py_TYPE(state);
	freefunc tp_free = PyType_GetSlot(tp, Py_tp_free);

	assert(tp_free != NULL);

	PyMem_Free(state->buff);
	tp_free(state);
	Py_DECREF(tp);
}

static PyObject *
getdents_next(struct getdents_state *s)
{
	if (s->bpos >= s->nread) {
		s->bpos = 0;
		s->nread = syscall(SYS_getdents64, s->fd, s->buff, s->buff_size);

		if (s->nread == 0)
			return NULL;

		if (s->nread == -1) {
			PyErr_SetString(PyExc_OSError, "getdents64");
			return NULL;
		}
	}

	struct linux_dirent64 *d = (struct linux_dirent64 *)(s->buff + s->bpos);

	PyObject *py_name = PyUnicode_DecodeFSDefault(d->d_name);

	PyObject *result = Py_BuildValue("KbO", d->d_ino, d->d_type, py_name);

	s->bpos += d->d_reclen;

	return result;
}

static PyType_Slot getdents_type_slots[] = {
	{Py_tp_alloc, PyType_GenericAlloc},
	{Py_tp_dealloc, getdents_dealloc},
	{Py_tp_iter, PyObject_SelfIter},
	{Py_tp_iternext, getdents_next},
	{Py_tp_new, getdents_new},
	{0, 0},
};

static PyType_Spec getdents_type_spec = {
	.name = "getdents.getdents_raw",
	.basicsize = sizeof(struct getdents_state),
	.flags = Py_TPFLAGS_DEFAULT,
	.slots = getdents_type_slots,
};

static struct PyModuleDef getdents_module = {
	PyModuleDef_HEAD_INIT,
	.m_name = "getdents",
	.m_doc = "",
	.m_size = -1,
};

PyMODINIT_FUNC
PyInit__getdents(void)
{
	PyObject *module = PyModule_Create(&getdents_module);

	if (!module)
		return NULL;

	PyObject *getdents_raw = PyType_FromSpec(&getdents_type_spec);

	if (!getdents_raw)
		return NULL;

	PyModule_AddObject(module, "getdents_raw", getdents_raw);
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
	return module;
}
