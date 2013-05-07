# Copyright 2011-2013 kwant authors.
#
# This file is part of kwant.  It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of kwant authors can be found in
# the AUTHORS file at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

#from nose.plugins.skip import Skip, SkipTest
from numpy.testing.decorators import skipif
try:
    from kwant.solvers.mumps import \
        solve, ldos, wave_function, options, reset_options
    import _test_sparse
    _no_mumps = False
except ImportError:
    _no_mumps = True


opt_list=[{},
          {'nrhs' : 1},
          {'nrhs' : 10},
          {'nrhs' : 1, 'ordering' : 'amd'},
          {'nrhs' : 10, 'sparse_rhs' : True},
          {'nrhs' : 2, 'ordering' : 'amd', 'sparse_rhs' : True}]


@skipif(_no_mumps)
def test_output():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_output(solve)


@skipif(_no_mumps)
def test_one_lead():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_one_lead(solve)


@skipif(_no_mumps)
def test_smatrix_shape():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_smatrix_shape(solve)


@skipif(_no_mumps)
def test_two_equal_leads():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_two_equal_leads(solve)

@skipif(_no_mumps)
def test_graph_system():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_graph_system(solve)


@skipif(_no_mumps)
def test_singular_graph_system():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_singular_graph_system(solve)


@skipif(_no_mumps)
def test_tricky_singular_hopping():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_tricky_singular_hopping(solve)


@skipif(_no_mumps)
def test_selfenergy():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_selfenergy(solve)


@skipif(_no_mumps)
def test_selfenergy_reflection():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_selfenergy_reflection(solve)


@skipif(_no_mumps)
def test_very_singular_leads():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_very_singular_leads(solve)


@skipif(_no_mumps)
def test_ldos():
    for opts in opt_list:
        reset_options()
        options(**opts)
        _test_sparse.test_ldos(ldos)


@skipif(_no_mumps)
def test_wavefunc_ldos_consistency():
    for opts in opt_list:
        options(**opts)
        _test_sparse.test_wavefunc_ldos_consistency(wave_function, ldos)
