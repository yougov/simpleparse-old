#if PY_MAJOR_VERSION >= 3
#define IS_PY3K

#define PyString_FromStringAndSize PyBytes_FromStringAndSize
#define PyString_AsString PyBytes_AsString
#define PyString_FromString PyBytes_FromString
#define PyString_Check PyBytes_Check
#define PyString_GET_SIZE PyBytes_GET_SIZE
#define PyString_AS_STRING PyBytes_AS_STRING
#define _PyString_Resize _PyBytes_Resize
#define PyInt_FromLong PyLong_FromLong
#define PyInt_Check PyLong_Check
#define PyInt_AS_LONG PyLong_AS_LONG

#endif

#ifndef Py_TYPE
    #define Py_TYPE(ob) (((PyObject*)(ob))->ob_type)
#endif
#define HAVE_UNICODE
#include "structmember.h"
