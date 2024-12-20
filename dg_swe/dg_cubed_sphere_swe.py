import numpy as np
from dg_swe.utils import gll, lagrange1st, cross_product, norm_L2
import torch
from matplotlib import pyplot as plt
from dg_swe.geometry import EquiangularFace, SadournyFace
from dg_swe.sbp_operators import dxd_m_SBP, dyd_m_SBP
import os


class DGCubedSphereSWE:
    def __init__(
            self, poly_order, nx, ny, g, f, eps, radius=1.0, device='cpu',
            solution=None, a=0.0, dtype=np.float32, damping=None,
            tau_func=lambda t, dt: t, tau=0, **kwargs):

        self.face_names = ['zp', 'zn', 'xp', 'xn', 'yp', 'yn']
        self.faces = {
            name: DGCubedSphereFace(
                name, poly_order, nx, ny, g, f, radius, eps, device, a=a, dtype=dtype, damping=None, bc='', tau=tau
            )
            for name in self.face_names
        }
        self.time = 0
        self.cdt = min(self.faces[n].cdt for n in self.face_names)
        self.damping = damping
        self.tau_func = tau_func
        self.flag = True

        self.time_list = []
        self.energy_list = []
        self.enstrophy_list = []
        self.mass_list = []
        self.vorticity_list = []
        self.H1 = True # calculates a continuous diagnostic vorticity for plotting

    def set_vort(self, sol):
        for name in self.face_names:
            face = self.faces[name]

    def boundaries(self, sol=None):

        if sol is None:
            sol = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}

        for name in self.face_names:

            face = self.faces[name]

            for con in face.connections:
                n, (i1, i2) = con

                neighbour = self.faces[n]
                u, v, w, h = sol[n]
                if i2 == 0:
                    u = u[:, -1]
                    v = v[:, -1]
                    w = w[:, -1]
                    h = h[:, -1]
                elif i2 == 1:
                    u = u[-1]
                    v = v[-1]
                    w = w[-1]
                    h = h[-1]
                elif i2 == 2:
                    u = u[:, 0]
                    v = v[:, 0]
                    w = w[:, 0]
                    h = h[:, 0]
                elif i2 == 3:
                    u = u[0]
                    v = v[0]
                    w = w[0]
                    h = h[0]
                else:
                    raise RuntimeError

                if i1 == 0:
                    # 0 - case of right element boundary. therefore fill array for right of element
                    face.u_right[-1] = u
                    face.v_right[-1] = v
                    face.w_right[-1] = w
                    face.h_right[-1] = h
                elif i1 == 1:
                    face.u_up[-1] = u
                    face.v_up[-1] = v
                    face.w_up[-1] = w
                    face.h_up[-1] = h
                elif i1 == 2:
                    # 2 - case of left element boundary. therefore fill array for right of element
                    face.u_left[0] = u
                    face.v_left[0] = v
                    face.w_left[0] = w
                    face.h_left[0] = h
                elif i1 == 3:
                    face.u_down[0] = u
                    face.v_down[0] = v
                    face.w_down[0] = w
                    face.h_down[0] = h
                else:
                    raise RuntimeError

    def get_dt(self):
        return min(face.get_dt() for face in self.faces.values())

    def time_step(self, dt=None, order=3, forcing=None):
        self.time_list.append(self.time)
        self.energy_list.append(self.integrate(self.entropy()))
        self.mass_list.append(self.integrate(self.mass()))

        self.h = {n: f.h for n, f in self.faces.items()}  # only needs to be done once
        if dt is None:
            dt = self.get_dt()

        if order == 3:

            u = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}
            self.boundaries(u)
            k_1 = {n: self.faces[n].solve(*u[n], self.time, dt) for n in self.face_names}

            u_1 = {n: tuple(u[n][i] + dt * k_1[n][i] for i in range(4)) for n in self.face_names}
            self.boundaries(u_1)
            k_2 = {n: self.faces[n].solve(*u_1[n], self.time, dt) for n in self.face_names}

            u_2 = {n: tuple(0.75 * u[n][i] + 0.25 * (u_1[n][i] + dt * k_2[n][i]) for i in range(4)) for n in self.face_names}
            self.boundaries(u_2)
            k_3 = {n: self.faces[n].solve(*u_2[n], self.time, dt) for n in self.face_names}

            for n in self.face_names:
                self.faces[n].u = (self.faces[n].u + 2 * (u_2[n][0] + dt * k_3[n][0])) / 3
                self.faces[n].v = (self.faces[n].v + 2 * (u_2[n][1] + dt * k_3[n][1])) / 3
                self.faces[n].w = (self.faces[n].w + 2 * (u_2[n][2] + dt * k_3[n][2])) / 3
                self.faces[n].h = (self.faces[n].h + 2 * (u_2[n][3] + dt * k_3[n][3])) / 3

            u = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}
            self.boundaries(u)

        elif order == 34:
            u = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}
            self.boundaries(u)
            k_1 = {n: self.faces[n].solve(*u[n], self.time, dt) for n in self.face_names}

            u_1 = {n: tuple(u[n][i] + 0.5 * dt * k_1[n][i] for i in range(4)) for n in self.face_names}
            self.boundaries(u_1)
            k_2 = {n: self.faces[n].solve(*u_1[n], self.time, dt) for n in self.face_names}

            u_2 = {n: tuple(u_1[n][i] + 0.5 * dt * k_2[n][i] for i in range(4)) for n in self.face_names}
            self.boundaries(u_2)
            k_3 = {n: self.faces[n].solve(*u_2[n], self.time, dt) for n in self.face_names}

            u_3 = {n: tuple((2 / 3) * u[n][i] + (1 / 3) * u_2[n][i] + (1 / 6) * dt * k_3[n][i] for i in range(4)) for n in self.face_names}
            self.boundaries(u_3)
            k_4 = {n: self.faces[n].solve(*u_3[n], self.time, dt) for n in self.face_names}

            for n in self.face_names:
                self.faces[n].u = u_3[n][0] + 0.5 * dt * k_4[n][0]
                self.faces[n].v = u_3[n][1] + 0.5 * dt * k_4[n][1]
                self.faces[n].w = u_3[n][2] + 0.5 * dt * k_4[n][2]
                self.faces[n].h = u_3[n][3] + 0.5 * dt * k_4[n][3]

            u = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}
            self.boundaries(u)

        for n in self.face_names:
            self.faces[n].time += dt

        self.time += dt

    def plot_solution(self, ax, vmin=None, vmax=None, plot_func=None, dim=3, cmap='nipy_spectral'):

        if dim == 3:
            return [self.faces[name].plot_solution(ax, vmin, vmax, plot_func, dim, cmap) for name in self.face_names]
        elif dim == 2:
            return [self.faces[name].plot_solution(ax, vmin, vmax, plot_func, dim, cmap) for name in self.face_names if name != 'zn']
        else:
            raise ValueError(f"dim: expected one of 2, 3. Found {dim}.")

    def triangular_plot(self, ax, vmin=None, vmax=None, plot_func=None, cmap='nipy_spectral', latlong=False, n=None, lines=False, levels=None):
        data = [plot_func(face).ravel() for face in self.faces.values()]
        if not latlong:
            x_coords = [face.xs.ravel() for face in self.faces.values()]
            y_coords = [face.ys.ravel() for face in self.faces.values()]
            z_coords = [face.zs.ravel() for face in self.faces.values()]
            z_coords = np.concatenate(z_coords)
        else:
            x_coords = [face.geometry.lat_long(face.xs, face.ys, face.zs)[1].ravel() for face in self.faces.values()]
            y_coords = [face.geometry.lat_long(face.xs, face.ys, face.zs)[0].ravel() for face in self.faces.values()]

        data = np.concatenate(data)
        y_coords = np.concatenate(y_coords)
        x_coords = np.concatenate(x_coords)

        if latlong:
            y_coords *= 180 / np.pi
            x_coords *= 180 / np.pi
            mask = (10 <= y_coords) & (y_coords <= 80)
        else:
            mask = z_coords > 0

        if n is None:
            n = int(0.5 * (vmax - vmin) / 1e-5)

        if levels is None:
            levels = np.linspace(vmin, vmax, n)
        print('Num levels', len(levels))

        if lines:
            out = ax.tricontour(
                -y_coords[mask], x_coords[mask], data[mask], colors='black',
                levels=levels, negative_linestyles='dashed', linewidths=0.5
            )
        else:
            out = ax.tricontourf(
                -y_coords[mask], x_coords[mask], data[mask], cmap=cmap, levels=levels
            )
        return [out]

    def latlong_triangular_plot(self, ax, vmin=None, vmax=None, plot_func=None, cmap='nipy_spectral', n=None, lines=False, levels=None):
        data = [plot_func(face).ravel() for face in self.faces.values()]

        x_coords = [face.geometry.lat_long(face.xs, face.ys, face.zs)[1].ravel() for face in self.faces.values()]
        y_coords = [face.geometry.lat_long(face.xs, face.ys, face.zs)[0].ravel() for face in self.faces.values()]

        data = np.concatenate(data)
        y_coords = np.concatenate(y_coords)
        x_coords = np.concatenate(x_coords)

        y_coords *= 180 / np.pi
        x_coords *= 180 / np.pi
        # mask = (10 <= y_coords) & (y_coords <= 80)
        mask = np.ones_like(x_coords) > 0

        if n is None:
            n = int(0.5 * (vmax - vmin) / 1e-5)

        if levels is None:
            levels = np.linspace(vmin, vmax, n)
        print('Num levels', len(levels))

        if lines:
            out = ax.tricontour(
                x_coords[mask], y_coords[mask], data[mask], colors='black',
                levels=levels, negative_linestyles='dashed', linewidths=0.5, inline=True
            )
            fntsz = 8
            label_set = list(levels[::5])
            if not levels[1] in label_set:
                label_set.append(levels[1])
            if not levels[-3] in label_set:
                label_set.append(levels[-3])
            print(label_set)
            ax.clabel(out, label_set, inline=True, fontsize=fntsz)
            # ax.clabel(out, out.levels[::5], inline=True, fontsize=fntsz)
            # ax.clabel(out, out.levels[:1], inline=True, fontsize=fntsz)
            # ax.clabel(out, out.levels[-1:], inline=True, fontsize=fntsz)
        else:
            out = ax.tricontourf(
                x_coords[mask], y_coords[mask], data[mask], cmap=cmap, levels=levels
            )
        return [out]

    def integrate(self, q):
        return sum(f.integrate(q[n]) for n, f in self.faces.items())

    def entropy(self):
        return {n: f.entropy() for n, f in self.faces.items()}

    def dEdt(self):
        return {n: f.dEdt() for n, f in self.faces.items()}

    def enstrophy(self):
        return {n: f.enstrophy() for n, f in self.faces.items()}

    def vorticity(self):
        return {n: f.h * f.q(f.u, f.v, f.w, f.h) for n, f in self.faces.items()}

    def mass(self):
        return {n: f.h for n, f in self.faces.items()}

    def save_restart(self, fn_template, directory):
        vars = ['u', 'v', 'w', 'h']
        state = {n: (self.faces[n].u, self.faces[n].v, self.faces[n].w, self.faces[n].h) for n in self.face_names}
        for name in self.face_names:
            for i in range(len(vars)):
                fp = self.make_fp(vars[i], name, fn_template, directory)
                data = state[name][i].numpy()
                np.save(fp, data)

    @staticmethod
    def make_fp(var, name, fn_template, directory):
        fn = f"{var}_{name}_{fn_template}"
        fp = os.path.join(directory, fn)
        return fp

    def load_restart(self, fn_template, directory):
        for name in self.face_names:
            vars = ['u', 'v', 'w', 'h']
            data = [np.load(self.make_fp(vars[i], name, fn_template, directory)) for i in range(len(vars))]
            b = self.faces[name].b
            self.faces[name].set_initial_condition(*data)
            self.faces[name].b = b

        self.boundaries()

    def save_diagnostics(self, fn_template, directory):
        diagnostics = np.stack([self.time_list, self.energy_list, self.mass_list])
        fp = os.path.join(directory, f"diagnostics_{fn_template}")
        np.save(fp, diagnostics)

    def plot_diagnostics(self, fn_template, directory, fig_int, label):

        diagnostics = np.load(os.path.join(directory, f"diagnostics_{fn_template}"))
        times = diagnostics[0] / (24 * 3600)
        entropy = diagnostics[1]
        mass = diagnostics[2]

        plt.figure(fig_int, figsize=(7, 7))

        tunit = ' (days)'
        plt.suptitle("Conservation errors")

        ax = plt.subplot(2, 2, 1)
        ax.set_ylabel("Energy error (normalized)")
        ax.set_xticks([], [])
        ax.plot(times, (entropy - entropy[0]) / entropy[0], label=label)
        ax.set_yscale('symlog', linthresh=1e-15)
        ax.grid(True, which='both')

        ax = plt.subplot(2, 2, 2)
        ax.set_ylabel("Mass error (normalized)")
        ax.set_xticks([], [])
        ax.plot(times, (mass - mass[0]) / mass[0], label=label)
        ax.set_yscale('symlog', linthresh=1e-16)
        ax.grid(True, which='both')

        plt.legend()
        plt.tight_layout()


class DGCubedSphereFace:
    """
    One face of the cubed sphere.
    """

    def __init__(
            self, name, poly_order, nx, ny, g, f, radius, eps, device='cpu',
            solution=None, a=0.0, dtype=np.float32, damping=None,
            tau_func=lambda t, dt: t, bc='wall', tau=0.0, **kwargs):

        valid_names = ['zp', 'zn', 'xp', 'xn', 'yp', 'yn']
        if not name in valid_names:
            raise ValueError(f'name: expected one of: {valid_names}. Found {name}.')
        self.name = name
        self.time = 0
        self.poly_order = poly_order
        self.u = None
        self.v = None
        self.h = None
        self.g = g
        self.eps = eps
        self.a = a
        self.solution = solution
        self.dtype = dtype
        self.damping = damping
        self.tau_func = tau_func
        self.xperiodic = self.yperiodic = False
        self.bc = bc
        self.geometry = EquiangularFace(name, radius=radius)
        self.connections = self.geometry.connections
        self.tau = tau
        


        x1 = np.linspace(-0.5, 0.5, nx)
        y1 = np.linspace(-0.5, 0.5, ny)
        
        lx = x1[1] - x1[0]
        ly = y1[1] - y1[0]
        self.dx = lx
        self.dy = ly

        weights_x = np.ones_like(x1)
        weights_x[0] = 17 / 48
        weights_x[1] = 59 / 48
        weights_x[2] = 43 / 48
        weights_x[3] = 49 / 48

        weights_x[-1] = 17 / 48
        weights_x[-2] = 59 / 48
        weights_x[-3] = 43 / 48
        weights_x[-4] = 49 / 48

        self.weights = weights_x[:, None] * weights_x[None, :]

        self.x1, self.y1 = np.meshgrid(x1, y1,indexing = 'xy')
        # 3D cartesian coordinates on surface of sphere
        self.xs, self.ys, self.zs = self.geometry.to_cartesian(self.x1, self.y1)
        lat, long = self.geometry.lat_long(self.xs, self.ys, self.zs)
        self.f = 2 * f * np.sin(lat)

        n = poly_order + 1

        self.device = torch.device(device)
        self.n = n
        self.sbp_boundary_weights = self.dx * 17.0/48.0
        # self.weights = torch.from_numpy(self.weights.astype(self.dtype)).to(self.device)
        # self.weights_x = torch.from_numpy(self.weights_x.astype(self.dtype)).to(self.device)
        self.nx = nx 
        self.ny = ny 
        
        self.cdt = eps * radius * min(lx, ly) / (2 * poly_order + 1)  # this should be multiplied by pi / (2 * sqrt(2)) = 1.11... but eh a slightly smaller time step can't hurt

        dxdx1, dxdy1, dxdz1, dydx1, dydy1, dydz1, dzdx1, dzdy1, dzdz1 = self.geometry.covariant_basis(self.x1, self.y1)
        self.dxdxi = torch.from_numpy(dxdx1.astype(self.dtype)).to(self.device) 
        self.dxdeta = torch.from_numpy(dxdy1.astype(self.dtype)).to(self.device) 
        self.dxdzeta = torch.from_numpy(self.xs.astype(self.dtype)).to(self.device) / radius
        #
        self.dydxi = torch.from_numpy(dydx1.astype(self.dtype)).to(self.device) 
        self.dydeta = torch.from_numpy(dydy1.astype(self.dtype)).to(self.device) 
        self.dydzeta = torch.from_numpy(self.ys.astype(self.dtype)).to(self.device) / radius
        #
        self.dzdxi = torch.from_numpy(dzdx1.astype(self.dtype)).to(self.device) 
        self.dzdeta = torch.from_numpy(dzdy1.astype(self.dtype)).to(self.device) 
        self.dzdzeta = torch.from_numpy(self.zs.astype(self.dtype)).to(self.device) / radius        


        cross = cross_product(
            [self.dxdxi, self.dydxi, self.dzdxi], [self.dxdzeta, self.dydzeta, self.dzdzeta]
        )
        self.J_vertface = torch.sqrt(sum(x_ ** 2 for x_ in cross))

        cross = cross_product(
            [self.dxdeta, self.dydeta, self.dzdeta], [self.dxdzeta, self.dydzeta, self.dzdzeta]
        )
        self.J_horzface = torch.sqrt(sum(x_ ** 2 for x_ in cross))

        self.J = self.dxdxi * (self.dydeta * self.dzdzeta - self.dydzeta * self.dzdeta)
        self.J += self.dydxi * (self.dzdeta * self.dxdzeta - self.dzdzeta * self.dxdeta)
        self.J += self.dzdxi * (self.dxdeta * self.dydzeta - self.dxdzeta * self.dydeta)
        self.J = self.J

        self.dxidx = (self.dydeta * self.dzdzeta - self.dydzeta * self.dzdeta) / self.J
        self.dxidy = (self.dzdeta * self.dxdzeta - self.dzdzeta * self.dxdeta) / self.J
        self.dxidz = (self.dxdeta * self.dydzeta - self.dxdzeta * self.dydeta) / self.J

        self.detadx = (self.dydzeta * self.dzdxi - self.dydxi * self.dzdzeta) / self.J
        self.detady = (self.dzdzeta * self.dxdxi - self.dzdxi * self.dxdzeta) / self.J
        self.detadz = (self.dxdzeta * self.dydxi - self.dxdxi * self.dydzeta) / self.J

        self.dzetadx = (self.dydxi * self.dzdeta - self.dydeta * self.dzdxi) / self.J
        self.dzetady = (self.dzdxi * self.dxdeta - self.dzdeta * self.dxdxi) / self.J
        self.dzetadz = (self.dxdxi * self.dydeta - self.dxdeta * self.dydxi) / self.J

        self.dxyzdzeta_norm = torch.sqrt(self.dxdzeta ** 2 + self.dydzeta ** 2 + self.dzdzeta ** 2)
        self.grad_zeta_norm = torch.sqrt(self.dzetadx ** 2 + self.dzetady ** 2 + self.dzetadz ** 2)

        self.kx = self.dzetadx / self.grad_zeta_norm
        self.ky = self.dzetady / self.grad_zeta_norm
        self.kz = self.dzetadz / self.grad_zeta_norm

        self.kx = torch.from_numpy(self.xs.astype(self.dtype)).to(self.device) / radius
        self.ky = torch.from_numpy(self.ys.astype(self.dtype)).to(self.device) / radius
        self.kz = torch.from_numpy(self.zs.astype(self.dtype)).to(self.device) / radius

        self.J_xi = np.sqrt(self.dxidx ** 2 + self.dxidy ** 2 + self.dxidz ** 2)
        self.J_eta = np.sqrt(self.detadx ** 2 + self.detady ** 2 + self.detadz ** 2)

        self.eta_x_up, self.eta_x_down = self.make_up_down_arrays(self.detadx / self.J_eta)
        self.eta_y_up, self.eta_y_down = self.make_up_down_arrays(self.detady / self.J_eta)
        self.eta_z_up, self.eta_z_down = self.make_up_down_arrays(self.detadz / self.J_eta)

        self.xi_x_right, self.xi_x_left = self.make_left_right_arrays(self.dxidx / self.J_xi)
        self.xi_y_right, self.xi_y_left = self.make_left_right_arrays(self.dxidy / self.J_xi)
        self.xi_z_right, self.xi_z_left = self.make_left_right_arrays(self.dxidz / self.J_xi)

        self.dxdxi_up, self.dxdxi_down = self.make_up_down_arrays(self.dxdxi)
        self.dydxi_up, self.dydxi_down = self.make_up_down_arrays(self.dydxi)
        self.dzdxi_up, self.dzdxi_down = self.make_up_down_arrays(self.dzdxi)

        self.dxdeta_right, self.dxdeta_left = self.make_left_right_arrays(self.dxdeta)
        self.dydeta_right, self.dydeta_left = self.make_left_right_arrays(self.dydeta)
        self.dzdeta_right, self.dzdeta_left = self.make_left_right_arrays(self.dzdeta)

        self.dxdxi_right, self.dxdxi_left = self.make_left_right_arrays(self.dxdxi)
        self.dydxi_right, self.dydxi_left = self.make_left_right_arrays(self.dydxi)
        self.dzdxi_right, self.dzdxi_left = self.make_left_right_arrays(self.dzdxi)

        self.dxdeta_up, self.dxdeta_down = self.make_up_down_arrays(self.dxdeta)
        self.dydeta_up, self.dydeta_down = self.make_up_down_arrays(self.dydeta)
        self.dzdeta_up, self.dzdeta_down = self.make_up_down_arrays(self.dzdeta)

        self.kx_up, self.kx_down = self.make_up_down_arrays(self.kx)
        self.ky_up, self.ky_down = self.make_up_down_arrays(self.ky)
        self.kz_up, self.kz_down = self.make_up_down_arrays(self.kz)

        self.kx_right, self.kx_left = self.make_left_right_arrays(self.kx)
        self.ky_right, self.ky_left = self.make_left_right_arrays(self.ky)
        self.kz_right, self.kz_left = self.make_left_right_arrays(self.kz)

    def make_left_right_arrays(self, arr):
        right_arr = torch.zeros((2, self.ny), dtype=self.dxdxi.dtype)
        left_arr = torch.zeros((2, self.ny), dtype=self.dxdxi.dtype)

        right_arr[:-1] = arr[:, 0]
        right_arr[-1] = arr[:, -1]

        left_arr[1:] = arr[:, -1]
        left_arr[0] = arr[:, 0]

        return right_arr, left_arr

    def make_up_down_arrays(self, arr):
        up_arr = torch.zeros((2, self.nx), dtype=self.dxdxi.dtype)
        down_arr = torch.zeros((2, self.nx), dtype=self.dxdxi.dtype)

        up_arr[:-1] = arr[0, :]
        up_arr[-1] = arr[-1, :]

        down_arr[1:] = arr[-1, :]
        down_arr[0] = arr[0, :]

        return up_arr, down_arr

    def boundaries(self, u, v, w, h, t):

        self.u_up[:-1] = u[0, :]
        self.u_down[1:] = u[-1, :]
        self.u_right[:-1] = u[:, 0]
        self.u_left[1:] = u[:, -1]

        self.v_up[:-1] = v[0, :]
        self.v_down[1:] = v[-1, :]
        self.v_right[:-1] = v[:, 0]
        self.v_left[1:] = v[:, -1]

        self.w_up[:-1] = w[0, :]
        self.w_down[1:] = w[-1, :]
        self.w_right[:-1] = w[:, 0]
        self.w_left[1:] = w[:, -1]

        self.h_up[:-1] = h[0, :]
        self.h_down[1:] = h[-1, :]
        self.h_right[:-1] = h[:, 0]
        self.h_left[1:] = h[:, -1]

        # wall boundary condition
        if self.bc.lower() == 'wall':
            self.h_up[-1] = h[-1, :, -1, :]
            self.h_down[0] = h[0, :, 0, :]
            self.h_right[:, -1] = h[:, -1, :, -1]
            self.h_left[:, 0] = h[:, 0, :, 0]

            u_, v_ = self.phys_to_contra(u, v, w)
            u_, v_, w_, = self.contra_to_phys(u_, 0 * v_)
            self.u_down[0], self.v_down[0], self.w_down[0] = u_[0, :, 0, :], v_[0, :, 0, :], w_[0, :, 0, :]
            self.u_up[-1], self.v_up[-1], self.w_up[-1] = u_[-1, :, -1, :], v_[-1, :, -1, :], w_[-1, :, -1, :]

            u_, v_ = self.phys_to_contra(u, v, w)
            u_, v_, w_, = self.contra_to_phys(0 * u_, v_)
            self.u_left[:, 0], self.v_left[:, 0], self.w_left[:, 0] = u_[:, 0, :, 0], v_[:, 0, :, 0], w_[:, 0, :, 0]
            self.u_right[:, -1], self.v_right[:, -1], self.w_right[:, -1] = u_[:, -1, :, -1], v_[:, -1, :, -1], w_[:, -1, :, -1]

    def apply_forcing(self, uk, vk, hk, t, forcing):
        uk_, vk_, hk_ = forcing(self.xs, self.ys, t)
        uk += torch.from_numpy(uk_.astype(self.dtype)).to(self.device)
        vk += torch.from_numpy(vk_.astype(self.dtype)).to(self.device)
        hk += torch.from_numpy(hk_.astype(self.dtype)).to(self.device)

    def get_dt(self):
        speed = self.wave_speed(self.u, self.v, self.w, self.h)
        dt = self.cdt / torch.max(speed).numpy()
        return dt

    def time_step(self, dt=None, order=3, forcing=None):
        if dt is None:
            dt = self.get_dt()

        if order == 3:
            uk_1, vk_1, wk_1, hk_1 = self.solve(self.u, self.v, self.w, self.h, self.time, dt)

            # SSPRK3
            u_1 = self.u + dt * uk_1
            v_1 = self.v + dt * vk_1
            w_1 = self.w + dt * wk_1
            h_1 = self.h + dt * hk_1

            uk_2, vk_2, wk_2, hk_2 = self.solve(u_1, v_1, w_1, h_1, self.time + dt, dt)

            u_2 = 0.75 * self.u + 0.25 * (u_1 + uk_2 * dt)
            v_2 = 0.75 * self.v + 0.25 * (v_1 + vk_2 * dt)
            w_2 = 0.75 * self.w + 0.25 * (w_1 + wk_2 * dt)
            h_2 = 0.75 * self.h + 0.25 * (h_1 + hk_2 * dt)
            uk_3, vk_3, wk_3, hk_3 = self.solve(u_2, v_2, w_2, h_2, self.time + 0.5 * dt, dt)

            self.u = (self.u + 2 * (u_2 + dt * uk_3)) / 3
            self.v = (self.v + 2 * (v_2 + dt * vk_3)) / 3
            self.w = (self.w + 2 * (w_2 + dt * wk_3)) / 3
            self.h = (self.h + 2 * (h_2 + dt * hk_3)) / 3
        else:
            raise ValueError(f"order: expected one of [3], found {order}.")

        self.time += dt

    def set_initial_condition(self, u, v, w, h, b=None):

        self.u = torch.from_numpy(u.astype(self.dtype)).to(self.device)
        self.v = torch.from_numpy(v.astype(self.dtype)).to(self.device)
        self.w = torch.from_numpy(w.astype(self.dtype)).to(self.device)

        self.h = torch.from_numpy(h.astype(self.dtype)).to(self.device)

        if b is None:
            self.b = torch.zeros_like(self.u).to(self.device)
        else:
            self.b = torch.from_numpy(b.astype(self.dtype)).to(self.device)


        self.tmp1 = torch.zeros_like(self.u).to(self.device)
        self.tmp2 = torch.zeros_like(self.u).to(self.device)

        self.u_left = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.u_right = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.u_up = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)
        self.u_down = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)

        self.v_left = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.v_right = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.v_up = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)
        self.v_down = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)

        self.w_left = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.w_right = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.w_up = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)
        self.w_down = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)

        self.h_left = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.h_right = torch.zeros((2, self.ny), dtype=self.tmp1.dtype).to(self.device)
        self.h_up = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)
        self.h_down = torch.zeros((2,self.nx), dtype=self.tmp1.dtype).to(self.device)

        self.boundaries(self.u, self.v, self.h, self.w, 0)

    def integrate(self, q):
        return (q * abs(self.J) * self.weights).sum()

    def entropy(self, u=None, v=None, w=None, h=None):
        if u is None:
            u = self.u
        if v is None:
            v = self.v
        if w is None:
            w = self.w
        if h is None:
            h = self.h
        return 0.5 * h * (u ** 2 + v ** 2 + w ** 2 + self.g * h)

    def dEdt(self):
        u, v, w, h = self.u, self.v, self.w, self.h
        dudt, dvdt, dwdt, dhdt = self.solve(u, v, w, h, 0, 0)
        # E = 0.5 * h * |u|^2 + 0.5 * g * h^2
        dEdt = h * (u * dudt + v * dvdt + w * dwdt)
        dEdt += (0.5 * (u ** 2 + v ** 2 + w ** 2) + self.g * h) * dhdt
        return dEdt


    def plot_solution(self, ax, vmin=None, vmax=None, plot_func=None, dim=3, cmap='nipy_spectral'):
        x_plot = self.xs.swapaxes(1, 2).reshape(self.h.shape[0] * self.h.shape[2], -1)
        y_plot = self.ys.swapaxes(1, 2).reshape(self.h.shape[0] * self.h.shape[2], -1)
        z_plot = self.zs.swapaxes(1, 2).reshape(self.h.shape[0] * self.h.shape[2], -1)

        if plot_func is None:
            data_plot = self.h.swapaxes(1, 2).reshape(self.h.shape[0] * self.h.shape[2], -1)
        else:
            out = plot_func(self)
            data_plot = out.swapaxes(1, 2).reshape(out.shape[0] * out.shape[2], -1)

        if dim == 3:
            from matplotlib import cm
            if vmin is None:
                vmin = data_plot.min()
            if vmax is None:
                vmax = data_plot.max()

            heatmap = data_plot - vmin
            heatmap /= (vmax - vmin)
            return ax.plot_surface(x_plot, y_plot, z_plot, cmap=cmap, vmin=vmin, vmax=vmax, facecolors=cm.jet(heatmap))
        elif dim == 2:
            if self.name in ['xp', 'yn']:
                idx = (z_plot.shape[0] // 2) + 1
                x_plot = x_plot[idx:]
                y_plot = y_plot[idx:]
                z_plot = z_plot[idx:]
                data_plot = data_plot[idx:]
            elif self.name in ['xn', 'yp']:
                idx = (z_plot.shape[1] // 2) + 1
                x_plot = x_plot[:, idx:]
                y_plot = y_plot[:, idx:]
                z_plot = z_plot[:, idx:]
                data_plot = data_plot[:, idx:]
            elif self.name == 'zn':
                raise ValueError('Face zn plotted.')

            # lat, long = self.geometry.lat_long(x_plot, y_plot, z_plot)
            #
            # import scipy
            # func = scipy.interpolate.interp2d(long.ravel(), lat.ravel(), data_plot.ravel())
            # lat = np.linspace(lat.min(), lat.max(), 100)
            # long = np.linspace(long.min(), long.max(), 100)
            # long, lat = np.meshgrid(long, lat)

            # return ax.contourf(long, lat, func(long, lat), cmap=cmap, vmin=vmin, vmax=vmax, levels=1000)
            return ax.contourf(x_plot, y_plot, data_plot, cmap=cmap, vmin=vmin, vmax=vmax, levels=1000)

    def imshow_solution(self, ax):
        u_plot = self.h.swapaxes(1, 2).reshape(self.h.shape[0] * self.h.shape[2], -1)

        return ax.contourf(u_plot)

    def hflux(self, u, v, w, h):
        yflux = v * h
        xflux = u * h
        zflux = w * h

        return xflux, yflux, zflux

    def uv_flux(self, u, v, w, h):
        return 0.5 * (u ** 2 + v ** 2 + w ** 2) + self.g * h

    def wave_speed(self, u, v, w, h):
        return torch.sqrt(u ** 2 + v ** 2 + w ** 2) + np.sqrt(self.g * h)

    def solve(self, u, v, w, h, t, dt, *, verbose=False):

        # copy the boundaries across
        self.boundaries(u, v, w, h, t)

        # handle h
        h_xflux, h_yflux, h_zflux = self.hflux(u, v, w, h)
        h_xflux, h_yflux = self.phys_to_contra(h_xflux, h_yflux, h_zflux)  # flux is in contravariant form
        
        div = dxd_m_SBP(h_xflux * self.J,self.nx,self.dx)
        div += dyd_m_SBP(h_yflux * self.J,self.ny,self.dy)

        div /= self.J

        out = -div

        h_up_flux_x, h_up_flux_y, h_up_flux_z = self.hflux(self.u_up, self.v_up, self.w_up, self.h_up)
        h_down_flux_x, h_down_flux_y, h_down_flux_z = self.hflux(self.u_down, self.v_down, self.w_down, self.h_down)
        h_right_flux_x, h_right_flux_y, h_right_flux_z = self.hflux(self.u_right, self.v_right, self.w_right, self.h_right)
        h_left_flux_x, h_left_flux_y, h_left_flux_z = self.hflux(self.u_left, self.v_left, self.w_left, self.h_left)

        # fluxes through boundary
        h_up_flux = h_up_flux_y * self.eta_y_up + h_up_flux_x * self.eta_x_up + h_up_flux_z * self.eta_z_up
        h_down_flux = h_down_flux_y * self.eta_y_down + h_down_flux_x * self.eta_x_down + h_down_flux_z * self.eta_z_down
        h_right_flux = h_right_flux_y * self.xi_y_right + h_right_flux_x * self.xi_x_right + h_right_flux_z * self.xi_z_right
        h_left_flux = h_left_flux_y * self.xi_y_left + h_left_flux_x * self.xi_x_left + h_left_flux_z * self.xi_z_left

        uv_up_flux = self.uv_flux(self.u_up, self.v_up, self.w_up, self.h_up)
        uv_down_flux = self.uv_flux(self.u_down, self.v_down, self.w_down, self.h_down)
        uv_right_flux = self.uv_flux(self.u_right, self.v_right, self.w_right, self.h_right)
        uv_left_flux = self.uv_flux(self.u_left, self.v_left, self.w_left, self.h_left)

        # upper boundary
        c_up = self.wave_speed(self.u_up, self.v_up, self.w_up, self.h_up)
        c_down = self.wave_speed(self.u_down, self.v_down, self.w_down, self.h_down)
        c_ve = 0.5 * (c_up + c_down)
        c_right = self.wave_speed(self.u_right, self.v_right, self.w_right, self.h_right)
        c_left = self.wave_speed(self.u_left, self.v_left, self.w_left, self.h_left)
        c_ho = 0.5 * (c_right + c_left)

        h_flux_vert = 0.5 * (h_up_flux + h_down_flux)
        h_flux_horz = 0.5 * (h_right_flux + h_left_flux)

        self.tmp1[-1] = (h_flux_vert[1:] - h_down_flux[1:]) * (self.J_vertface[-1])
        self.tmp1[0] = -(h_flux_vert[:-1] - h_up_flux[:-1]) * (self.J_vertface[0])
        self.tmp2[:, -1] = (h_flux_horz[1:] - h_left_flux[1:]) * (self.J_horzface[..., -1])
        self.tmp2[:, 0] = -(h_flux_horz[:-1] - h_right_flux[:-1]) * (self.J_horzface[..., 0])
        
        boundary_sbp_integration_weight = 17.0 / 48.0
        out -= (self.tmp1 + self.tmp2) / (self.J * self.sbp_boundary_weights)        
        
        h_k = out

        # u and v fluxes
        ########
        #######

        uv_flux = self.uv_flux(u, v, w, h)

        alpha = torch.maximum(c_right / self.h_right, c_left / self.h_left)
        uv_flux_horz = 0.5 * (uv_right_flux + uv_left_flux) - self.a * (h_right_flux - h_left_flux) * alpha #(self.g / c_ho)
        alpha = torch.maximum(c_up / self.h_up, c_down / self.h_down)
        uv_flux_vert = 0.5 * (uv_up_flux + uv_down_flux) - self.a * (h_up_flux - h_down_flux) * alpha #(self.g / c_ve) * (h_up_flux - h_down_flux)

        if self.b is not None:
            uv_flux += self.g * self.b

        velocity_perp = cross_product([self.kx, self.ky, self.kz], [u, v, w])
        u_perp, v_perp, _ = self.phys_to_cov(*velocity_perp)
        #
        u_cov, v_cov, _ = self.phys_to_cov(u, v, w)
        vort = dxd_m_SBP(v_cov,self.nx,self.dx)
        vort -= dyd_m_SBP(u_cov,self.ny,self.dy)
        vort /= self.J
        vort += self.f

        #
        #
        u_cov_up = self.u_up * self.dxdxi_up + self.v_up * self.dydxi_up + self.w_up * self.dzdxi_up
        u_cov_down = self.u_down * self.dxdxi_down + self.v_down * self.dydxi_down + self.w_down * self.dzdxi_down

        v_cov_right = self.u_right * self.dxdeta_right + self.v_right * self.dydeta_right + self.w_right * self.dzdeta_right
        v_cov_left = self.u_left * self.dxdeta_left + self.v_left * self.dydeta_left + self.w_left * self.dzdeta_left

        vel_p_up = cross_product([self.kx_up, self.ky_up, self.kz_up], [self.u_up, self.v_up, self.w_up])
        u_perp_up = vel_p_up[0] * self.dxdxi_up + vel_p_up[1] * self.dydxi_up + vel_p_up[2] * self.dzdxi_up
        v_perp_up = vel_p_up[0] * self.dxdeta_up + vel_p_up[1] * self.dydeta_up + vel_p_up[2] * self.dzdeta_up

        vel_p_down = cross_product([self.kx_down, self.ky_down, self.kz_down], [self.u_down, self.v_down, self.w_down])
        u_perp_down = vel_p_down[0] * self.dxdxi_down + vel_p_down[1] * self.dydxi_down + vel_p_down[2] * self.dzdxi_down
        v_perp_down = vel_p_down[0] * self.dxdeta_down + vel_p_down[1] * self.dydeta_down + vel_p_down[2] * self.dzdeta_down

        vel_p_right = cross_product([self.kx_right, self.ky_right, self.kz_right], [self.u_right, self.v_right, self.w_right])
        u_perp_right = vel_p_right[0] * self.dxdxi_right + vel_p_right[1] * self.dydxi_right + vel_p_right[2] * self.dzdxi_right
        v_perp_right = vel_p_right[0] * self.dxdeta_right + vel_p_right[1] * self.dydeta_right + vel_p_right[2] * self.dzdeta_right

        vel_p_left = cross_product([self.kx_left, self.ky_left, self.kz_left], [self.u_left, self.v_left, self.w_left])
        u_perp_left = vel_p_left[0] * self.dxdxi_left + vel_p_left[1] * self.dydxi_left + vel_p_left[2] * self.dzdxi_left
        v_perp_left = vel_p_left[0] * self.dxdeta_left + vel_p_left[1] * self.dydeta_left + vel_p_left[2] * self.dzdeta_left

        # handle u
        #######
        ###

        out = -dxd_m_SBP(uv_flux, self.nx , self.dx)
        out -= vort * u_perp

        self.tmp1[-1] = 0
        self.tmp1[0] = 0
        self.tmp2[:, -1] = (uv_flux_horz - uv_left_flux)[1:] * (self.J_horzface / self.J_xi)[..., -1]
        self.tmp2[:, 0] = -(uv_flux_horz - uv_right_flux)[:-1] * (self.J_horzface / self.J_xi)[..., 0]
        
        self.tmp1[-1] += -0.5 * (u_perp_down * (u_cov_up - u_cov_down))[1] * (self.J_vertface / (self.J_eta * self.J))[-1]
        self.tmp1[0] += -0.5 * (u_perp_up * (u_cov_up - u_cov_down))[0] * (self.J_vertface / (self.J_eta * self.J))[0]
        self.tmp2[:, -1] += 0.5 * (u_perp_left * (v_cov_right - v_cov_left))[1] * (self.J_horzface / (self.J_xi * self.J))[..., -1]
        self.tmp2[:, 0] += 0.5 * (u_perp_right * (v_cov_right - v_cov_left))[0] * (self.J_horzface / (self.J_xi * self.J))[..., 0]

        out -= (self.tmp1 + self.tmp2) / (self.J * self.sbp_boundary_weights)
        u_k = out

        # handle v
        #######
        ###

        out = -dyd_m_SBP(uv_flux, self.ny, self.dy)
        out -= vort * v_perp

        self.tmp1[-1] = (uv_flux_vert - uv_down_flux)[1:] * (self.J_vertface / self.J_eta)[-1]
        self.tmp1[0] = -(uv_flux_vert - uv_up_flux)[:-1] * (self.J_vertface / self.J_eta)[0]
        self.tmp2[:, -1] = 0
        self.tmp2[:, 0] = 0

        self.tmp1[-1] += -0.5 * (v_perp_down * (u_cov_up - u_cov_down))[1] * (self.J_vertface / (self.J_eta * self.J))[-1]
        self.tmp1[0] += -0.5 * (v_perp_up * (u_cov_up - u_cov_down))[0] * (self.J_vertface / (self.J_eta * self.J))[0]
        self.tmp2[:, -1] += 0.5 * (v_perp_left * (v_cov_right - v_cov_left))[1] * (self.J_horzface / (self.J_xi * self.J))[..., -1]
        self.tmp2[:, 0] += 0.5 * (v_perp_right * (v_cov_right - v_cov_left))[0] * (self.J_horzface / (self.J_xi * self.J))[..., 0]

        out -= (self.tmp1 + self.tmp2) / (self.J * self.sbp_boundary_weights)
        v_k = out

        u_k, v_k, w_k = self.cov_to_phys(u_k, v_k, 0)

        if verbose:
            print('dudt max:', abs(u_k).max())
            print('dvdt max:', abs(v_k).max())
            print('dwdt max:', abs(w_k).max())
            print('dhdt max:', abs(h_k).max())               
        return u_k, v_k, w_k, h_k

    def phys_to_contra(self, u, v, w):
        u_contra = u * self.dxidx + v * self.dxidy + w * self.dxidz
        v_contra = u * self.detadx + v * self.detady + w * self.detadz
        return u_contra, v_contra

    def phys_to_cov(self, u, v, w):
        u_cov = u * self.dxdxi + v * self.dydxi + w * self.dzdxi
        v_cov = u * self.dxdeta + v * self.dydeta + w * self.dzdeta
        w_cov = u * self.dxdzeta + v * self.dydzeta + w * self.dzdzeta
        return u_cov, v_cov, w_cov

    def cov_to_phys(self, u_cov, v_cov, w_cov):
        u = u_cov * self.dxidx + v_cov * self.detadx + w_cov * self.dzetadx
        v = u_cov * self.dxidy + v_cov * self.detady + w_cov * self.dzetady
        w = u_cov * self.dxidz + v_cov * self.detadz + w_cov * self.dzetadz
        return u, v, w

    def contra_to_phys(self, u_contra, v_contra):
        u = u_contra * self.dxdxi + v_contra * self.dxdeta
        v = u_contra * self.dydxi + v_contra * self.dydeta
        w = u_contra * self.dzdxi + v_contra * self.dzdeta
        return u, v, w

    def k_dot_curl(self, u, v, w):
        u_cov, v_cov, w_cov = self.phys_to_cov(u, v, w)
        out = torch.einsum('fgcd,abcd->fgab', v_cov, self.ddxi) - torch.einsum('fgcd,abcd->fgab', u_cov, self.ddeta)
        return out / self.J

    def curl_k(self, psi):
        cov_psi_k = psi * norm_L2([self.dxdzeta, self.dydzeta, self.dzdzeta])
        u_contra = -torch.einsum('fgcd,abcd->fgab', cov_psi_k, self.ddeta) / self.J
        v_contra = torch.einsum('fgcd,abcd->fgab', cov_psi_k, self.ddxi) / self.J

        u, v, w = self.contra_to_phys(u_contra, v_contra)
        return u, v, w

    def k_cross_grad(self, psi):
        u_cov = torch.einsum('fgcd,abcd->fgab', psi, self.ddxi)
        v_cov = torch.einsum('fgcd,abcd->fgab', psi, self.ddeta)

        u, v, w = self.cov_to_phys(u_cov, v_cov, 0)
        u, v, w = cross_product([self.kx, self.ky, self.kz], [u, v, w])
        return u, v, w
