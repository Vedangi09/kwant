# Copyright 2011-2013 Kwant authors.
#
# This file is part of Kwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of Kwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

import tempfile
import warnings
import itertools
import numpy as np
import tinyarray as ta
from math import cos, sin, pi
import scipy.integrate
import pytest

import kwant
from kwant import plotter
from kwant._common import ensure_rng

if plotter.mpl_enabled:
    from mpl_toolkits import mplot3d
    from matplotlib import pyplot  # pragma: no flakes


def test_importable_without_matplotlib():
    prefix, sep, suffix = plotter.__file__.rpartition('.')
    if suffix in ['pyc', 'pyo']:
        suffix = 'py'
    assert suffix == 'py'
    fname = sep.join((prefix, suffix))
    with open(fname) as f:
        code = f.read()
    code = code.replace('from . import', 'from kwant import')
    code = code.replace('matplotlib', 'totalblimp')

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        exec(code)               # Trigger the warning.
        assert len(w) == 1
        assert issubclass(w[0].category, RuntimeWarning)
        assert "only iterator-providing functions" in str(w[0].message)


def syst_2d(W=3, r1=3, r2=8):
    a = 1
    t = 1.0
    lat = kwant.lattice.square(a, norbs=1)
    syst = kwant.Builder()

    def ring(pos):
        (x, y) = pos
        rsq = x ** 2 + y ** 2
        return r1 ** 2 < rsq < r2 ** 2

    syst[lat.shape(ring, (0, r1 + 1))] = 4 * t
    syst[lat.neighbors()] = -t
    sym_lead0 = kwant.TranslationalSymmetry(lat.vec((-1, 0)))
    lead0 = kwant.Builder(sym_lead0)
    lead2 = kwant.Builder(sym_lead0)

    lead_shape = lambda pos: (-W / 2 < pos[1] < W / 2)

    lead0[lat.shape(lead_shape, (0, 0))] = 4 * t
    lead2[lat.shape(lead_shape, (0, 0))] = 4 * t
    syst.attach_lead(lead2)
    lead0[lat.neighbors()] = - t
    lead1 = lead0.reversed()
    syst.attach_lead(lead0)
    syst.attach_lead(lead1)
    return syst


def syst_3d(W=3, r1=2, r2=4, a=1, t=1.0):
    lat = kwant.lattice.general(((a, 0, 0), (0, a, 0), (0, 0, a)))
    syst = kwant.Builder()

    def ring(pos):
        (x, y, z) = pos
        rsq = x ** 2 + y ** 2
        return (r1 ** 2 < rsq < r2 ** 2) and abs(z) < 2
    syst[lat.shape(ring, (0, -r2 + 1, 0))] = 4 * t
    syst[lat.neighbors()] = - t
    sym_lead0 = kwant.TranslationalSymmetry(lat.vec((-1, 0, 0)))
    lead0 = kwant.Builder(sym_lead0)

    lead_shape = lambda pos: (-W / 2 < pos[1] < W / 2) and abs(pos[2]) < 2

    lead0[lat.shape(lead_shape, (0, 0, 0))] = 4 * t
    lead0[lat.neighbors()] = - t
    lead1 = lead0.reversed()
    syst.attach_lead(lead0)
    syst.attach_lead(lead1)
    return syst


@pytest.mark.skipif(not plotter.mpl_enabled, reason="No matplotlib available.")
def test_plot():
    plot = plotter.plot
    syst2d = syst_2d()
    syst3d = syst_3d()
    color_opts = ['k', (lambda site: site.tag[0]),
                  lambda site: (abs(site.tag[0] / 100),
                                abs(site.tag[1] / 100), 0)]
    with tempfile.TemporaryFile('w+b') as out:
        for color in color_opts:
            for syst in (syst2d, syst3d):
                fig = plot(syst, site_color=color, cmap='binary', file=out)
                if (color != 'k' and
                    isinstance(color(next(iter(syst2d.sites()))), float)):
                    assert fig.axes[0].collections[0].get_array() is not None
                assert len(fig.axes[0].collections) == (8 if syst is syst2d else
                                                        6)
        color_opts = ['k', (lambda site, site2: site.tag[0]),
                      lambda site, site2: (abs(site.tag[0] / 100),
                                           abs(site.tag[1] / 100), 0)]
        for color in color_opts:
            for syst in (syst2d, syst3d):
                fig = plot(syst2d, hop_color=color, cmap='binary', file=out,
                           fig_size=(2, 10), dpi=30)
                if color != 'k' and isinstance(color(next(iter(syst2d.sites())),
                                                          None), float):
                    assert fig.axes[0].collections[1].get_array() is not None

        assert isinstance(plot(syst3d, file=out).axes[0], mplot3d.axes3d.Axes3D)

        syst2d.leads = []
        plot(syst2d, file=out)
        del syst2d[list(syst2d.hoppings())]
        plot(syst2d, file=out)

        plot(syst3d, file=out)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plot(syst2d.finalized(), file=out)

def good_transform(pos):
    x, y = pos
    return y, x

def bad_transform(pos):
    x, y = pos
    return x, y, 0

@pytest.mark.skipif(not plotter.mpl_enabled, reason="No matplotlib available.")
def test_map():
    syst = syst_2d()
    with tempfile.TemporaryFile('w+b') as out:
        plotter.map(syst, lambda site: site.tag[0], pos_transform=good_transform,
                    file=out, method='linear', a=4, oversampling=4, cmap='flag')
        pytest.raises(ValueError, plotter.map, syst,
                      lambda site: site.tag[0],
                      pos_transform=bad_transform, file=out)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plotter.map(syst.finalized(), range(len(syst.sites())),
                        file=out)
        pytest.raises(ValueError, plotter.map, syst,
                      range(len(syst.sites())), file=out)


def test_mask_interpolate():
    # A coordinate array with coordinates of two points almost coinciding.
    coords = np.array([[0, 0], [1e-7, 1e-7], [1, 1], [1, 0]])

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        plotter.mask_interpolate(coords, np.ones(len(coords)), a=1)
        assert len(w) == 1
        assert issubclass(w[-1].category, RuntimeWarning)
        assert "coinciding" in str(w[-1].message)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pytest.raises(ValueError, plotter.mask_interpolate,
                      coords, np.ones(len(coords)))
        pytest.raises(ValueError, plotter.mask_interpolate,
                      coords, np.ones(2 * len(coords)))


@pytest.mark.skipif(not plotter.mpl_enabled, reason="No matplotlib available.")
def test_bands():

    syst = syst_2d().finalized().leads[0]

    with tempfile.TemporaryFile('w+b') as out:
        plotter.bands(syst, file=out)
        plotter.bands(syst, fig_size=(10, 10), file=out)
        plotter.bands(syst, momenta=np.linspace(0, 2 * np.pi), file=out)

        fig = pyplot.Figure()
        ax = fig.add_subplot(1, 1, 1)
        plotter.bands(syst, ax=ax, file=out)


@pytest.mark.skipif(not plotter.mpl_enabled, reason="No matplotlib available.")
def test_spectrum():

    def ham_1d(a, b, c):
        return a**2 + b**2 + c**2

    def ham_2d(a, b, c):
        return np.eye(2) * (a**2 + b**2 + c**2)

    lat = kwant.lattice.chain()
    syst = kwant.Builder()
    syst[(lat(i) for i in range(3))] = lambda site, a, b: a + b
    syst[lat.neighbors()] = lambda site1, site2, c: c
    fsyst = syst.finalized()

    vals = np.linspace(0, 1, 3)

    with tempfile.TemporaryFile('w+b') as out:

        for ham in (ham_1d, ham_2d, fsyst):
            plotter.spectrum(ham, ('a', vals), params=dict(b=1, c=1), file=out)
            # test with explicit figsize
            plotter.spectrum(ham, ('a', vals), params=dict(b=1, c=1),
                             fig_size=(10, 10), file=out)

        for ham in (ham_1d, ham_2d, fsyst):
            plotter.spectrum(ham, ('a', vals), ('b', 2 * vals),
                             params=dict(c=1), file=out)
            # test with explicit figsize
            plotter.spectrum(ham, ('a', vals), ('b', 2 * vals),
                             params=dict(c=1), fig_size=(10, 10), file=out)

        # test 2D plot and explicitly passing axis
        fig = pyplot.Figure()
        ax = fig.add_subplot(1, 1, 1, projection='3d')
        plotter.spectrum(ham_1d, ('a', vals), ('b', 2 * vals),
                         params=dict(c=1), ax=ax, file=out)
        # explicitly pass axis without 3D support
        ax = fig.add_subplot(1, 1, 1)
        with pytest.raises(TypeError):
            plotter.spectrum(ham_1d, ('a', vals), ('b', 2 * vals),
                             params=dict(c=1), ax=ax, file=out)

    def mask(a, b):
        return a > 0.5

    with tempfile.TemporaryFile('w+b') as out:
        plotter.spectrum(ham, ('a', vals), ('b', 2 * vals), params=dict(c=1),
                         mask=mask, file=out)


def syst_rect(lat, salt, W=3, L=50):
    syst = kwant.Builder()

    ll = L//2
    ww = W//2

    def onsite(site):
        return 4 + 0.1 * kwant.digest.gauss(site.tag, salt=salt)

    syst[(lat(i, j) for i in range(-ll, ll+1)
         for j in range(-ww, ww+1))] = onsite
    syst[lat.neighbors()] = -1

    sym = kwant.TranslationalSymmetry(lat.vec((-1, 0)))
    lead = kwant.Builder(sym)
    lead[(lat(0, j) for j in range(-ww, ww + 1))] = 4
    lead[lat.neighbors()] = -1

    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())

    return syst


def div(F):
    """Calculate the divergence of a vector field F."""
    assert len(F.shape[:-1]) == F.shape[-1]
    return sum(np.gradient(F[..., i])[i] for i in range(F.shape[-1]))


def rotational_currents(g):
    """Return a basis of divergence-free currents for a closed graph.

    Given the graph 'g' of a Kwant system, returns a sequence of arrays
    which are linearly independent, divergence-free currents on the graph.
    """
    #'A' represents the set of expressions that give the net current flow
    # into the system sites. 'perm' is a map from the edges of a graph
    # with only 1 edge per hopping to the proper Kwant graph (2 edges
    # per hopping).
    A = np.zeros((g.num_nodes, g.num_edges // 2))
    hoppings = dict()
    perm_data = np.zeros(g.num_edges)
    perm_ij = np.zeros((2, g.num_edges))
    i = 0
    for k, (a, b) in enumerate(g):
        hop = frozenset((a, b))
        if hop not in hoppings:
            A[a, i] = 1
            A[b, i] = -1
            hoppings[hop] = i
            perm_data[k] = 1
            perm_ij[:, k] = (k, i)
            i += 1
        else:
            perm_data[k] = -1
            perm_ij[:, k] = (k, hoppings[hop])

    perm = scipy.sparse.coo_matrix((perm_data, perm_ij))

    # Get the row vectors of V with singular value 0. These form
    # a basis for the right null space of 'A'.
    U, S, V = np.linalg.svd(A)
    tol = S.max() * max(A.shape) * np.finfo(S.dtype).eps
    rank = sum(S > tol)
    # Transform null space basis into vectors defined over the full
    # hopping space (both hopping directions).
    null_space_basis = V[-(len(V) - rank):].transpose()
    null_space_basis = perm.dot(null_space_basis).transpose()
    return null_space_basis


def test_current_interpolation():

    ## Passing a Builder will raise an error
    pytest.raises(TypeError, plotter.interpolate_current, syst_2d(), None)

    def R(theta):
        return ta.array([[cos(theta), -sin(theta)], [sin(theta), cos(theta)]])

    def make_lattice(a, theta):
        x = ta.dot(R(theta), (a, 0))
        y = ta.dot(R(theta), (0, a))
        return kwant.lattice.general([x, y], norbs=1)

    angles = (0, pi/6, pi/4)
    lat_constants = (1, 2)

    ## Check current through cross section is same for different lattice
    ## parameters and orientations of the system wrt. the discretization grid
    for a, theta in itertools.product(lat_constants, angles):
        lat = make_lattice(a, theta)
        syst = syst_rect(lat, salt='0').finalized()
        psi = kwant.wave_function(syst, energy=3)(0)

        def cut(a, b):
            return b.tag[0] < 0 and a.tag[0] >= 0

        J = kwant.operator.Current(syst).bind()
        J_cut = kwant.operator.Current(syst, where=cut, sum=True).bind()
        (x, y), j0 = plotter.interpolate_current(syst, J(psi[0]), gauss_range=5)

        # slice field perpendicular to a cut along the y axis
        y_axis = (np.argmin(np.abs(x)), slice(None), 0)
        ## Integrate and compare with summed current.
        assert np.isclose(J_cut(psi[0]),
                          scipy.integrate.simps(j0[y_axis], y))

    ## Check that taking a finer grid or changing the broadening does not
    ## affect the total integrated current.
    n_s = (3, 5)
    sigma_s = (1, 0.5)

    for n, sigma in zip(n_s, sigma_s):
        (x, y), j0 = plotter.interpolate_current(syst, J(psi[0]), n=n,
                                                 sigma=sigma, gauss_range=5)
        # slice field perpendicular to a cut along the y axis
        y_axis = (np.argmin(np.abs(x)), slice(None), 0)
        assert np.isclose(J_cut(psi[0]),
                          scipy.integrate.simps(j0[y_axis], y))

    ### Tests on a divergence-free current (closed system)

    lat = kwant.lattice.general([(1, 0), (0.5, np.sqrt(3) / 2)])
    syst = kwant.Builder()
    sites = [lat(0, 0), lat(1, 0), lat(0, 1), lat(2, 2)]
    syst[sites] = None
    syst[((s, t) for s, t in itertools.product(sites, sites) if s != t)] = None
    del syst[lat(0, 0), lat(2, 2)]
    syst = syst.finalized()

    # generate random divergence-free currents
    Js = rotational_currents(syst.graph)
    rng = ensure_rng(3)
    J0 = sum(rng.rand(len(Js))[:, None] * Js)
    J1 = sum(rng.rand(len(Js))[:, None] * Js)

    # Sanity check that diverence on the graph is 0
    divergence = np.zeros(len(syst.sites))
    for (a, _), current in zip(syst.graph, J0):
        divergence[a] += current
    assert np.allclose(divergence, 0)

    _, j0 = plotter.interpolate_current(syst, J0)
    _, j1 = plotter.interpolate_current(syst, J1)

    ## Test linearity of interpolation.
    _, j_tot = plotter.interpolate_current(syst, J0 + 2 * J1)
    assert np.allclose(j_tot, j0 + 2 * j1)

    ## Test that divergence of interpolated current is approximately zero.
    # For currents not aligned with the interpolation grid this is only
    # 1/a**2 accurate.
    _, j = plotter.interpolate_current(syst, J0, n=20, gauss_range=4)
    div_j = np.max(np.abs(div(j)))
    assert np.isclose(div_j, 0, atol=1E-4)


@pytest.mark.skipif(not plotter.mpl_enabled, reason="No matplotlib available.")
def test_current():
    syst = syst_2d().finalized()
    J = kwant.operator.Current(syst)
    current = J(kwant.wave_function(syst, energy=1)(1)[0])

    # Test good codepath
    with tempfile.TemporaryFile('w+b') as out:
        plotter.current(syst, current, file=out)

        fig = pyplot.Figure()
        ax = fig.add_subplot(1, 1, 1)
        plotter.current(syst, current, ax=ax, file=out)
