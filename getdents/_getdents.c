#include <Python.h>
#include <dirent.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
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
	bool   ready_for_next_batch;
};


#ifndef O_GETDENTS
# define O_GETDENTS (O_DIRECTORY | O_RDONLY | O_NONBLOCK | O_CLOEXEC)
#endif

#ifndef MIN_GETDENTS_BUFF_SIZE
# define MIN_GETDENTS_BUFF_SIZE (MAXNAMLEN + sizeof(struct linux_dirent64))
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

	struct getdents_state *state = (void *) type->tp_alloc(type, 0);

	if (!state)
		return NULL;

	void *buff = malloc(buff_size);

	if (!buff)
		return PyErr_NoMemory();

	state->buff = buff;
	state->buff_size = buff_size;
	state->fd = fd;
	state->bpos = 0;
	state->nread = 0;
	state->ready_for_next_batch = true;
	return (PyObject *) state;
}

static void
getdents_dealloc(struct getdents_state *state)
{
	free(state->buff);
	Py_TYPE(state)->tp_free(state);
}

static PyObject *
getdents_next(struct getdents_state *s)
{
	s->ready_for_next_batch = s->bpos >= s->nread;

	if (s->ready_for_next_batch) {
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

PyTypeObject getdents_type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"getdents_raw",                 /* tp_name */
	sizeof(struct getdents_state),  /* tp_basicsize */
	0,                              /* tp_itemsize */
	(destructor) getdents_dealloc,  /* tp_dealloc */
	0,                              /* tp_print */
	0,                              /* tp_getattr */
	0,                              /* tp_setattr */
	0,                              /* tp_reserved */
	0,                              /* tp_repr */
	0,                              /* tp_as_number */
	0,                              /* tp_as_sequence */
	0,                              /* tp_as_mapping */
	0,                              /* tp_hash */
	0,                              /* tp_call */
	0,                              /* tp_str */
	0,                              /* tp_getattro */
	0,                              /* tp_setattro */
	0,                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,             /* tp_flags */
	0,                              /* tp_doc */
	0,                              /* tp_traverse */
	0,                              /* tp_clear */
	0,                              /* tp_richcompare */
	0,                              /* tp_weaklistoffset */
	PyObject_SelfIter,              /* tp_iter */
	(iternextfunc) getdents_next,   /* tp_iternext */
	0,                              /* tp_methods */
	0,                              /* tp_members */
	0,                              /* tp_getset */
	0,                              /* tp_base */
	0,                              /* tp_dict */
	0,                              /* tp_descr_get */
	0,                              /* tp_descr_set */
	0,                              /* tp_dictoffset */
	0,                              /* tp_init */
	PyType_GenericAlloc,            /* tp_alloc */
	getdents_new,                   /* tp_new */
};

static struct PyModuleDef getdents_module = {
	PyModuleDef_HEAD_INIT,
	"getdents",                      /* m_name */
	"",                              /* m_doc */
	-1,                              /* m_size */
};

PyMODINIT_FUNC
PyInit__getdents(void)
{
	if (PyType_Ready(&getdents_type) < 0)
		return NULL;

	PyObject *module = PyModule_Create(&getdents_module);

	if (!module)
		return NULL;

	Py_INCREF(&getdents_type);
	PyModule_AddObject(module, "getdents_raw", (PyObject *) &getdents_type);
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
