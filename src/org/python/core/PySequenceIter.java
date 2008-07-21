/* Copyright (c) Jython Developers */
package org.python.core;

/**
 * General sequence iterator.
 */
public class PySequenceIter extends PyIterator {

    private PyObject seq;

    private int index = 0;

    public PySequenceIter(PyObject seq) {
        this.seq = seq;
    }

    public PyObject __iternext__() {
        try {
            return seq.__finditem__(index++);
        } catch (PyException exc) {
            if (Py.matchException(exc, Py.StopIteration)) {
                return null;
            }
            throw exc;
        }
    }
}
