import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体支持
rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "sans-serif"]
rcParams["axes.unicode_minus"] = False

import plotly.graph_objects as go
from scipy.interpolate import griddata


def detect_wafer_radius(x, y):
    """
    根据数据点的最大半径识别晶圆的标准尺寸

    Args:
        x, y: 数据点坐标数组

    Returns:
        wafer_radius: 晶圆标准半径（米）
        wafer_size_inch: 晶圆尺寸（英寸）
    """
    # 计算数据点的最大半径
    data_radius = np.max(np.sqrt(x**2 + y**2))

    # 标准晶圆尺寸（半径，米）
    standard_sizes = {
        2: 0.025,  # 2英寸 = 50mm
        3: 0.038,  # 3英寸 = 76mm
        4: 0.050,  # 4英寸 = 100mm
        6: 0.075,  # 6英寸 = 150mm
        8: 0.100,  # 8英寸 = 200mm
        12: 0.150,  # 12英寸 =
    }

    # 找到最接近的标准尺寸
    best_size = None
    min_diff = float("inf")

    for size_inch, radius in standard_sizes.items():
        diff = abs(data_radius - radius)
        if diff < min_diff:
            min_diff = diff
            best_size = size_inch

    wafer_radius = standard_sizes[best_size]

    return wafer_radius, best_size


def remove_tilt(x, y, z):
    """拟合平面 z = ax + by + c 并返回残差"""
    A = np.c_[x, y, np.ones(len(x))]
    coeff, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
    a, b, c = coeff
    z_fit = a * x + b * y + c
    return z - z_fit


def calculate_surface_form(x, y, z):
    """去除一阶面形并计算PV值"""
    z_resid = remove_tilt(x, y, z)
    pv = np.max(z_resid) - np.min(z_resid)
    return z_resid, pv


def calculate_dynamic_sfma(
    x,
    y,
    z,
    slit_w=0.026,
    slit_h=0.008,
    slit_step_x=0.013,
    slit_step_y=0.001,
):
    """
    动态移动狭缝模拟 (SFMA)
    蛇形移动:从左下角开始,向上移动,然后向右移动一列,再向下移动,如此往复
    每次移除局部倾斜,累积残差并计算均值

    参数:
        x, y, z: 数据点坐标和高度值
        slit_w, slit_h: 狭缝的宽度和高度,单位米
        slit_step_x: slit在X方向的移动步长,单位米 (默认: 0.013m = 13mm)
        slit_step_y: slit在Y方向的移动步长,单位米 (默认: 0.001m = 1mm)
    """

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    n_cols = int(round((max_x - min_x) / step_x)) + 1
    n_rows = int(round((max_y - min_y) / step_y)) + 1

    col_indices = np.round((x - min_x) / step_x).astype(int)
    row_indices = np.round((y - min_y) / step_y).astype(int)

    grid_z = np.full((n_rows, n_cols), np.nan)
    grid_z[row_indices, col_indices] = z

    grid_x = min_x + np.arange(n_cols) * step_x
    grid_y = min_y + np.arange(n_rows) * step_y
    GX, GY = np.meshgrid(grid_x, grid_y)

    slit_px_w = int(round(slit_w / step_x))
    slit_px_h = int(round(slit_h / step_y))
    slit_step_px_x = max(1, int(round(slit_step_x / step_x)))  # X方向移动步长(像素)
    slit_step_px_y = max(1, int(round(slit_step_y / step_y)))  # Y方向移动步长(像素)

    # 使用均值累积
    layout_sum = np.zeros((n_rows, n_cols))
    layout_count = np.zeros((n_rows, n_cols))

    # 蛇形移动: 使用物理距离步长(转换为像素)
    for col_idx, col_start_idx in enumerate(range(-slit_px_w, n_cols, slit_step_px_x)):
        col_end_idx = col_start_idx + slit_px_w
        valid_start = max(0, col_start_idx)
        valid_end = min(n_cols, col_end_idx)

        if valid_start >= valid_end:
            continue

        col_z = grid_z[:, valid_start:valid_end]
        col_x = GX[:, valid_start:valid_end]
        col_y = GY[:, valid_start:valid_end]

        # 偶数列向上(从0开始),奇数列向下(从最大开始)
        if col_idx % 2 == 0:
            y_range = range(0, n_rows - slit_px_h + 1, slit_step_px_y)
        else:
            y_range = range(n_rows - slit_px_h, -1, -slit_step_px_y)

        for y_start_idx in y_range:
            y_end_idx = y_start_idx + slit_px_h

            win_z = col_z[y_start_idx:y_end_idx, :]
            win_x = col_x[y_start_idx:y_end_idx, :]
            win_y = col_y[y_start_idx:y_end_idx, :]

            mask = ~np.isnan(win_z)
            if np.sum(mask) < 10:
                continue

            z_f = win_z[mask]
            x_f = win_x[mask]
            y_f = win_y[mask]

            A = np.c_[x_f, y_f, np.ones(len(x_f))]
            coeff, _, _, _ = np.linalg.lstsq(A, z_f, rcond=None)
            a, b, c = coeff

            z_fit = a * win_x + b * win_y + c
            residual = win_z - z_fit

            valid_res_mask = ~np.isnan(residual)
            acc_sum_slice = layout_sum[y_start_idx:y_end_idx, valid_start:valid_end]
            acc_count_slice = layout_count[y_start_idx:y_end_idx, valid_start:valid_end]

            # 累积求和和计数
            acc_sum_slice[valid_res_mask] += residual[valid_res_mask]
            acc_count_slice[valid_res_mask] += 1

    # 计算均值
    with np.errstate(divide="ignore", invalid="ignore"):
        result_map = layout_sum / layout_count

    z_dynamic = result_map[row_indices, col_indices]
    return z_dynamic


def calculate_local_tilt(x, y, z):
    """
    计算局部倾斜角度 (梯度幅值)
    使用中心差分法计算X和Y方向斜率,边缘使用前向/后向差分,角点使用局部平面拟合
    """

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    n_cols = int(round((max_x - min_x) / step_x)) + 1
    n_rows = int(round((max_y - min_y) / step_y)) + 1

    grid_z = np.full((n_rows, n_cols), np.nan)
    col_indices = np.round((x - min_x) / step_x).astype(int)
    row_indices = np.round((y - min_y) / step_y).astype(int)

    col_indices = np.clip(col_indices, 0, n_cols - 1)
    row_indices = np.clip(row_indices, 0, n_rows - 1)

    grid_z[row_indices, col_indices] = z

    slope_x = np.full((n_rows, n_cols), np.nan)
    slope_y = np.full((n_rows, n_cols), np.nan)

    def fit_local_plane(i, j, grid_z, step_x, step_y):
        """拟合3x3邻域的平面并返回斜率"""
        points_x, points_y, points_z = [], [], []

        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                ni, nj = i + di, j + dj
                if 0 <= ni < grid_z.shape[0] and 0 <= nj < grid_z.shape[1]:
                    if not np.isnan(grid_z[ni, nj]):
                        points_x.append(nj * step_x)
                        points_y.append(ni * step_y)
                        points_z.append(grid_z[ni, nj])

        if len(points_z) >= 3:
            A = np.c_[points_x, points_y, np.ones(len(points_z))]
            try:
                coeff, _, _, _ = np.linalg.lstsq(A, points_z, rcond=None)
                return coeff[0], coeff[1]
            except:
                return np.nan, np.nan
        return np.nan, np.nan

    for i in range(n_rows):
        for j in range(n_cols):
            if np.isnan(grid_z[i, j]):
                continue

            is_left_edge = j == 0
            is_right_edge = j == n_cols - 1
            is_top_edge = i == 0
            is_bottom_edge = i == n_rows - 1

            is_corner = (is_left_edge or is_right_edge) and (
                is_top_edge or is_bottom_edge
            )
            is_edge = (
                is_left_edge or is_right_edge or is_top_edge or is_bottom_edge
            ) and not is_corner

            if is_corner:
                # 角点使用局部平面拟合
                sx, sy = fit_local_plane(i, j, grid_z, step_x, step_y)
                slope_x[i, j] = sx
                slope_y[i, j] = sy
            elif is_edge:
                # 边缘点使用双侧差分(如果可能),否则使用单侧差分
                # X方向
                if is_left_edge:
                    if (
                        j + 2 < n_cols
                        and not np.isnan(grid_z[i, j + 1])
                        and not np.isnan(grid_z[i, j + 2])
                    ):
                        # 使用前向二阶差分
                        slope_x[i, j] = (
                            -3 * grid_z[i, j] + 4 * grid_z[i, j + 1] - grid_z[i, j + 2]
                        ) / (2 * step_x)
                    elif not np.isnan(grid_z[i, j + 1]):
                        slope_x[i, j] = (grid_z[i, j + 1] - grid_z[i, j]) / step_x
                elif is_right_edge:
                    if (
                        j - 2 >= 0
                        and not np.isnan(grid_z[i, j - 1])
                        and not np.isnan(grid_z[i, j - 2])
                    ):
                        # 使用后向二阶差分
                        slope_x[i, j] = (
                            3 * grid_z[i, j] - 4 * grid_z[i, j - 1] + grid_z[i, j - 2]
                        ) / (2 * step_x)
                    elif not np.isnan(grid_z[i, j - 1]):
                        slope_x[i, j] = (grid_z[i, j] - grid_z[i, j - 1]) / step_x
                else:
                    # 顶部或底部边缘,X方向可以用中心差分
                    if not np.isnan(grid_z[i, j + 1]) and not np.isnan(
                        grid_z[i, j - 1]
                    ):
                        slope_x[i, j] = (grid_z[i, j + 1] - grid_z[i, j - 1]) / (
                            2 * step_x
                        )

                # Y方向
                if is_top_edge:
                    if (
                        i + 2 < n_rows
                        and not np.isnan(grid_z[i + 1, j])
                        and not np.isnan(grid_z[i + 2, j])
                    ):
                        # 使用前向二阶差分
                        slope_y[i, j] = (
                            -3 * grid_z[i, j] + 4 * grid_z[i + 1, j] - grid_z[i + 2, j]
                        ) / (2 * step_y)
                    elif not np.isnan(grid_z[i + 1, j]):
                        slope_y[i, j] = (grid_z[i + 1, j] - grid_z[i, j]) / step_y
                elif is_bottom_edge:
                    if (
                        i - 2 >= 0
                        and not np.isnan(grid_z[i - 1, j])
                        and not np.isnan(grid_z[i - 2, j])
                    ):
                        # 使用后向二阶差分
                        slope_y[i, j] = (
                            3 * grid_z[i, j] - 4 * grid_z[i - 1, j] + grid_z[i - 2, j]
                        ) / (2 * step_y)
                    elif not np.isnan(grid_z[i - 1, j]):
                        slope_y[i, j] = (grid_z[i, j] - grid_z[i - 1, j]) / step_y
                else:
                    # 左侧或右侧边缘,Y方向可以用中心差分
                    if not np.isnan(grid_z[i + 1, j]) and not np.isnan(
                        grid_z[i - 1, j]
                    ):
                        slope_y[i, j] = (grid_z[i + 1, j] - grid_z[i - 1, j]) / (
                            2 * step_y
                        )
            else:
                # 内部点使用局部平面拟合
                sx, sy = fit_local_plane(i, j, grid_z, step_x, step_y)
                slope_x[i, j] = sx
                slope_y[i, j] = sy

    slope_x_urad = slope_x * 1e6
    slope_y_urad = slope_y * 1e6

    tilt_urad_grid = np.full_like(slope_x_urad, np.nan)
    mask_both = ~np.isnan(slope_x_urad) & ~np.isnan(slope_y_urad)
    tilt_urad_grid[mask_both] = np.sqrt(
        slope_x_urad[mask_both] ** 2 + slope_y_urad[mask_both] ** 2
    )

    mask_only_x = ~np.isnan(slope_x_urad) & np.isnan(slope_y_urad)
    tilt_urad_grid[mask_only_x] = np.abs(slope_x_urad[mask_only_x])

    mask_only_y = np.isnan(slope_x_urad) & ~np.isnan(slope_y_urad)
    tilt_urad_grid[mask_only_y] = np.abs(slope_y_urad[mask_only_y])

    tilt_urad = tilt_urad_grid[row_indices, col_indices]
    return tilt_urad


def calculate_nce(x, y, z, field_size_x=0.026, field_size_y=0.008, offset_x=0.0):
    """计算NCE(非可校正误差),对每个场移除局部倾斜"""
    z_nce = np.full_like(z, np.nan)

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    # 从数据推断物理间距
    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    start_x = min_x + offset_x
    n_cols = int(np.ceil((max_x - start_x) / field_size_x)) + 1
    n_rows = int(np.ceil((max_y - min_y) / field_size_y))

    x_edges = start_x + np.arange(n_cols + 1) * field_size_x
    y_edges = min_y + np.arange(n_rows + 1) * field_size_y

    grid_lines_x = x_edges
    grid_lines_y = y_edges

    expected_points = (field_size_x * field_size_y) / (step_x * step_y)
    min_points = max(10, int(expected_points * 0.1))

    for i in range(len(x_edges) - 1):
        for j in range(len(y_edges) - 1):
            x_start, x_end = x_edges[i], x_edges[i + 1]
            y_start, y_end = y_edges[j], y_edges[j + 1]

            mask = (x >= x_start) & (x < x_end) & (y >= y_start) & (y < y_end)

            if np.sum(mask) > min_points:
                x_field = x[mask]
                y_field = y[mask]
                z_field = z[mask]

                A = np.c_[x_field, y_field, np.ones(len(x_field))]
                coeff, _, _, _ = np.linalg.lstsq(A, z_field, rcond=None)
                a, b, c = coeff
                z_fit = a * x_field + b * y_field + c

                z_nce[mask] = z_field - z_fit

    return z_nce, grid_lines_x, grid_lines_y


def plot_sfma_heatmap(x, y, z_sfma, metric_val, output_image_path, wafer_radius=None):
    """生成SFMA热力图"""
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(z_sfma)
    if np.sum(mask) == 0:
        plt.close(fig)
        return

    cntr = ax.tricontourf(x[mask], y[mask], z_sfma[mask], levels=100, cmap=cmap)
    cbar = fig.colorbar(cntr, ax=ax)
    cbar.formatter.set_powerlimits((0, 0))

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    ax.add_patch(circle)

    ax.axis("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"SFMA\nm3s = {metric_val * 1e9:.2f} nm")

    fig.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    # print(f"Saved SFMA heatmap to {output_image_path}")


def plot_sfma_high_heatmap(
    x, y, z_sfma, threshold, output_image_path, wafer_radius=None
):
    """生成大于特定阈值的SFMA热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    # threshold is in meters, convert to nm for display comparison if needed,
    # but here we compare in meters as z_sfma is in meters.
    # threshold passed in is in meters.

    mask = (~np.isnan(z_sfma)) & (np.abs(z_sfma) > threshold)

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius

    if np.sum(mask) == 0:
        plt.text(
            0.5,
            0.5,
            f"No data > {threshold * 1e9:.1f} nm",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )
    else:
        sc = plt.scatter(x[mask], y[mask], c=z_sfma[mask], cmap=cmap, s=5)
        cbar = plt.colorbar(sc)
        cbar.formatter.set_powerlimits((0, 0))

    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"SFMA (> {threshold * 1e9:.1f} nm)")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()


def plot_high_pv_heatmap(
    x, y, z_resid, threshold, output_image_path, wafer_radius=None
):
    """生成大于特定阈值的PV热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    # threshold is in meters
    mask = (~np.isnan(z_resid)) & (np.abs(z_resid) > threshold)

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius

    if np.sum(mask) == 0:
        plt.text(
            0.5,
            0.5,
            f"No data > {threshold * 1e6:.1f} μm",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )
    else:
        sc = plt.scatter(x[mask], y[mask], c=z_resid[mask], cmap=cmap, s=5)
        cbar = plt.colorbar(sc)
        cbar.formatter.set_powerlimits((0, 0))

    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"去一阶面形 (> {threshold * 1e6:.1f} μm)")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()


def plot_surface_heatmap(x, y, z_resid, pv, output_image_path, wafer_radius=None):
    """生成去一阶面形后的热力图"""
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("jet")
    cntr = ax.tricontourf(x, y, z_resid, levels=100, cmap=cmap)
    cbar = fig.colorbar(cntr, ax=ax)
    cbar.formatter.set_powerlimits((0, 0))

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    ax.add_patch(circle)

    ax.axis("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"去一阶面形\nPV = {pv * 1e6:.2f} um")

    fig.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    # print(f"Saved heatmap to {output_image_path}")


def plot_tilt_heatmap(
    x,
    y,
    tilt_urad,
    mean_val,
    std_val,
    max_val,
    metric_val,
    output_image_path,
    wafer_radius=None,
):
    """生成局部倾斜角度热力图"""
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(tilt_urad)
    if np.sum(mask) == 0:
        print("No valid tilt data to plot.")
        plt.close(fig)
        return

    cntr = ax.tricontourf(x[mask], y[mask], tilt_urad[mask], levels=100, cmap=cmap)
    cbar = fig.colorbar(cntr, ax=ax)
    cbar.set_label("μrad")

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    ax.add_patch(circle)

    ax.axis("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"局部角分布\nmax= {max_val:.2f} μrad, m3s = {metric_val:.2f} μrad")

    fig.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    # print(f"Saved tilt heatmap to {output_image_path}")


def plot_high_tilt_heatmap(
    x, y, tilt_urad, threshold, output_image_path, wafer_radius=None
):
    """生成大于特定阈值的局部倾斜角度热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = (~np.isnan(tilt_urad)) & (tilt_urad > threshold)

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius

    if np.sum(mask) == 0:
        # 如果没有超过阈值的点，生成一个空图或者提示图
        plt.text(
            0.5,
            0.5,
            f"No data > {threshold} μrad",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )
    else:
        # 使用 scatter 绘制散点，因为超过阈值的区域可能是不连续的
        sc = plt.scatter(x[mask], y[mask], c=tilt_urad[mask], cmap=cmap, s=5)
        cbar = plt.colorbar(sc)
        cbar.set_label("μrad")

    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"局部角分布 (大于{threshold}μrad区域)")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved high tilt heatmap to {output_image_path}")


def plot_nce_heatmap(
    x, y, z_nce, std_val, grid_x, grid_y, output_image_path, wafer_radius=None
):
    """生成NCE面形热力图"""
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(z_nce)
    if np.sum(mask) == 0:
        print("No valid NCE data to plot.")
        plt.close(fig)
        return

    cntr = ax.tricontourf(x[mask], y[mask], z_nce[mask], levels=100, cmap=cmap)
    cbar = fig.colorbar(cntr, ax=ax)
    cbar.formatter.set_powerlimits((0, 0))

    for gx in grid_x:
        ax.axvline(gx, color="k", linewidth=0.5)
    for gy in grid_y:
        ax.axhline(gy, color="k", linewidth=0.5)

    # 使用晶圆标准半径画圆形轮廓，如果未提供则使用数据最大半径
    if wafer_radius is None:
        r = np.max(np.sqrt(x**2 + y**2))
    else:
        r = wafer_radius
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    ax.add_patch(circle)

    ax.axis("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"NCE面形（96场布局）\n3std = {3 * std_val * 1e9:.2f} nm")

    fig.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    # print(f"Saved NCE heatmap to {output_image_path}")


def generate_plotly_heatmap(
    x,
    y,
    z,
    title,
    metric_text=None,
    circle_radius=None,
    zmin=None,
    zmax=None,
    z_label=None,
    interpolate=True,
    mask_threshold=None,
    mask_mode="abs_gt",
):
    """
    Generate a Plotly Figure for heatmap.
    """
    # 1. Interpolate Grid for Smoothness (Upsampling)
    # Target resolution for smooth rendering
    res = 600

    # Filter NaNs from input data before interpolation
    valid_mask = ~np.isnan(z)
    if np.sum(valid_mask) < 4:
        pass

    x_valid = x[valid_mask]
    y_valid = y[valid_mask]
    z_valid = z[valid_mask]

    # Define limits based on input data
    if len(x_valid) > 0:
        xmin, xmax = np.min(x_valid), np.max(x_valid)
        ymin, ymax = np.min(y_valid), np.max(y_valid)
    else:
        xmin, xmax = np.min(x), np.max(x)
        ymin, ymax = np.min(y), np.max(y)

    # Create high-res grid
    xi = np.linspace(xmin, xmax, res)
    yi = np.linspace(ymin, ymax, res)
    Xi, Yi = np.meshgrid(xi, yi)

    Zi = None
    # Interpolate using linear method
    if interpolate and len(x_valid) > 4:
        try:
            points = np.column_stack((x_valid, y_valid))
            Zi = griddata(points, z_valid, (Xi, Yi), method="linear")
        except Exception as e:
            print(f"Interpolation failed: {e}")
            Zi = None

    # Fallback to raw data if needed
    if Zi is None or np.all(np.isnan(Zi)):
        # print("Fallback to raw data heatmap")
        x_rounded = np.round(x, 9)
        y_rounded = np.round(y, 9)
        xi_final = np.sort(np.unique(x_rounded))
        yi_final = np.sort(np.unique(y_rounded))

        x_map = {v: i for i, v in enumerate(xi_final)}
        y_map = {v: i for i, v in enumerate(yi_final)}
        Zi_final = np.full((len(yi_final), len(xi_final)), np.nan)

        for v_x, v_y, v_z in zip(x_rounded, y_rounded, z):
            if not np.isnan(v_z) and v_y in y_map and v_x in x_map:
                Zi_final[y_map[v_y], x_map[v_x]] = v_z

        final_x, final_y, final_z = xi_final, yi_final, Zi_final
    else:
        final_x, final_y, final_z = xi, yi, Zi

    # Apply Post-Interpolation Masking
    if mask_threshold is not None:
        if mask_mode == "abs_gt":
            mask = np.abs(final_z) > mask_threshold
        elif mask_mode == "gt":
            mask = final_z > mask_threshold
        else:
            mask = np.ones_like(final_z, dtype=bool)

        final_z = np.where(mask, final_z, np.nan)

    # 2. Configure Layout
    layout = go.Layout(
        title=dict(
            text=title + (f"<br>{metric_text}" if metric_text else ""),
            x=0.5,  # Center title
            xanchor="center",
            yanchor="top",
        ),
        xaxis=dict(
            title="X (m)",
            scaleanchor="y",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Y (m)",
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
        ),
        width=600,
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        autosize=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    fig = go.Figure(layout=layout)

    # 3. Add Heatmap
    fig.add_trace(
        go.Heatmap(
            x=final_x,
            y=final_y,
            z=final_z,
            colorscale="Jet",
            zmin=zmin,
            zmax=zmax,
            colorbar=dict(
                title=z_label,
                thickness=15,
                exponentformat="power",  # e.g. 10^-8
                showexponent="all",
                tickformat=".1g",  # General format, will use sci notation for small numbers
            ),
            zsmooth="best",
            connectgaps=False,
            hovertemplate="X: %{x:.4f} m<br>Y: %{y:.4f} m<br>Val: %{z:.4g} "
            + (z_label if z_label else "")
            + "<extra></extra>",
        )
    )

    # 4. Add Circle Border
    if circle_radius:
        # B. Add Black Border Circle
        fig.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=-circle_radius,
            y0=-circle_radius,
            x1=circle_radius,
            y1=circle_radius,
            line=dict(color="black", width=2),
            fillcolor="rgba(0,0,0,0)",
        )

        # Update axes to fit circle with some padding (1.1x like before)
        limit = circle_radius * 1.1
        fig.update_xaxes(range=[-limit, limit])
        fig.update_yaxes(range=[-limit, limit])

    return fig


def generate_plotly_scatter(
    x,
    y,
    z,
    title,
    circle_radius=None,
    zmin=None,
    zmax=None,
    z_label=None,
):
    """
    Generate a Plotly Figure using Scattergl (dots).
    Ideal for threshold/sparse data visualization.
    """
    # Configure Layout (Reuse standard layout settings)
    layout = go.Layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        xaxis=dict(
            title="X (m)",
            scaleanchor="y",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Y (m)",
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
        ),
        width=600,
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        autosize=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    fig = go.Figure(layout=layout)

    # Add ScatterGL trace
    fig.add_trace(
        go.Scattergl(
            x=x,
            y=y,
            mode="markers",
            marker=dict(
                size=4,  # Adjust dot size to mimic plt.scatter(s=5)
                color=z,  # Color by value
                colorscale="Jet",
                cmin=zmin,
                cmax=zmax,
                colorbar=dict(
                    title=z_label,
                    thickness=15,
                    exponentformat="power",
                    showexponent="all",
                    tickformat=".1g",
                ),
            ),
            hovertemplate="X: %{x:.4f} m<br>Y: %{y:.4f} m<br>Val: %{marker.color:.4g} "
            + (z_label if z_label else "")
            + "<extra></extra>",
        )
    )

    # Add Circle Border
    if circle_radius:
        fig.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=-circle_radius,
            y0=-circle_radius,
            x1=circle_radius,
            y1=circle_radius,
            line=dict(color="black", width=2),
            fillcolor="rgba(0,0,0,0)",
        )
        limit = circle_radius * 1.1
        fig.update_xaxes(range=[-limit, limit])
        fig.update_yaxes(range=[-limit, limit])

    return fig


def calculate_roa_profile(
    x,
    y,
    z,
    reference_radius_min=0.020,
    reference_radius_max=0.100,
    edge_radius_start=0.120,
    wafer_radius=None,
    bin_width=0.0005,
    reference_fit="quadratic",
):
    """
    Calculate ROA from a radial median surface profile.

    ROA(R) = z_ref(R) - z_profile(R), so a downward edge roll-off produces a
    positive ROA. Radius is computed from finite raw x/y/z points, then binned
    into a robust median radial profile before fitting the internal reference.
    """
    radius = np.sqrt(x**2 + y**2)
    valid_mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(z) & np.isfinite(radius)
    if np.sum(valid_mask) < 4:
        return None

    radius_mm = radius[valid_mask] * 1000
    z_nm = z[valid_mask] * 1e9

    if wafer_radius is None:
        wafer_radius_mm = np.nanmax(radius_mm)
    else:
        wafer_radius_mm = wafer_radius * 1000

    bin_width_mm = max(bin_width * 1000, 0.001)
    bins = np.arange(0, wafer_radius_mm + bin_width_mm, bin_width_mm)
    if len(bins) < 2:
        return None

    profile_r = []
    profile_z = []
    profile_inner = []
    profile_outer = []
    for start, end in zip(bins[:-1], bins[1:]):
        bin_mask = (radius_mm >= start) & (radius_mm < end)
        if np.sum(bin_mask) < 3:
            continue
        profile_r.append((start + end) / 2)
        profile_z.append(np.nanmedian(z_nm[bin_mask]))
        profile_inner.append(start)
        profile_outer.append(end)

    profile_r = np.array(profile_r)
    profile_z = np.array(profile_z)
    profile_inner = np.array(profile_inner)
    profile_outer = np.array(profile_outer)
    if len(profile_r) < 3:
        return None

    smooth_surface = profile_z.copy()
    if len(smooth_surface) >= 7:
        from scipy.signal import savgol_filter

        window = min(
            41,
            len(smooth_surface) if len(smooth_surface) % 2 == 1 else len(smooth_surface) - 1,
        )
        window = max(7, window)
        if window % 2 == 0:
            window -= 1
        if window > 3:
            smooth_surface = savgol_filter(smooth_surface, window, polyorder=3)

    ref_min_mm = reference_radius_min * 1000
    ref_max_mm = reference_radius_max * 1000
    if ref_min_mm > ref_max_mm:
        ref_min_mm, ref_max_mm = ref_max_mm, ref_min_mm
    ref_min_mm = np.clip(ref_min_mm, 0, wafer_radius_mm)
    ref_max_mm = np.clip(ref_max_mm, ref_min_mm, wafer_radius_mm)

    ref_mask = (profile_r >= ref_min_mm) & (profile_r <= ref_max_mm)
    if np.sum(ref_mask) < 2:
        ref_mask = np.isfinite(profile_z)

    fit_mode = reference_fit.lower()
    max_degree = {"constant": 0, "linear": 1, "quadratic": 2}.get(fit_mode, 1)
    degree = min(max_degree, max(0, np.sum(ref_mask) - 1))

    if degree == 0:
        coeff = np.array([np.nanmedian(profile_z[ref_mask])])
        z_ref = np.full_like(profile_z, coeff[0], dtype=float)
        raw_z_ref = np.full_like(z_nm, coeff[0], dtype=float)
    else:
        coeff = np.polyfit(profile_r[ref_mask], profile_z[ref_mask], degree)
        z_ref = np.polyval(coeff, profile_r)
        raw_z_ref = np.polyval(coeff, radius_mm)

    roa = z_ref - profile_z
    reference_level = np.nanmedian(z_ref[ref_mask])
    raw_display_height = z_nm - raw_z_ref
    display_surface_profile = smooth_surface - z_ref
    raw_leveled_height = raw_display_height + reference_level
    leveled_surface_profile = display_surface_profile + reference_level

    edge_start_mm = np.clip(edge_radius_start * 1000, 0, wafer_radius_mm)
    edge_mask = profile_r >= edge_start_mm
    if not np.any(edge_mask):
        edge_mask = profile_r >= profile_r[-1]

    edge_roa = roa[edge_mask]
    max_roa = np.nanmax(edge_roa) if len(edge_roa) else np.nan

    weights = profile_outer[edge_mask] ** 2 - profile_inner[edge_mask] ** 2
    valid_weights = np.isfinite(edge_roa) & np.isfinite(weights) & (weights > 0)
    if np.any(valid_weights):
        weighted_mean = np.sum(edge_roa[valid_weights] * weights[valid_weights])
        weighted_mean /= np.sum(weights[valid_weights])
    else:
        weighted_mean = np.nan

    p99_roa = np.nanpercentile(edge_roa, 99) if len(edge_roa) else np.nan

    return {
        "raw_radius": radius_mm,
        "raw_height": z_nm,
        "raw_display_height": raw_display_height,
        "raw_leveled_height": raw_leveled_height,
        "radius": profile_r,
        "surface_profile": profile_z,
        "smooth_surface_profile": smooth_surface,
        "display_surface_profile": display_surface_profile,
        "leveled_surface_profile": leveled_surface_profile,
        "reference_profile": z_ref,
        "reference_level": reference_level,
        "roa_profile": roa,
        "reference_radius_min": ref_min_mm,
        "reference_radius_max": ref_max_mm,
        "edge_radius_start": edge_start_mm,
        "wafer_radius": wafer_radius_mm,
        "reference_fit": fit_mode,
        "max_roa": max_roa,
        "weighted_mean_roa": weighted_mean,
        "p99_roa": p99_roa,
    }


def generate_roa_figure(profile):
    """Generate a report-style radial surface profile for ROA analysis."""
    fig = go.Figure()

    raw_radius = profile["raw_radius"]
    raw_height = profile["raw_leveled_height"]
    max_points = 30000
    if len(raw_radius) > max_points:
        rng = np.random.default_rng(0)
        sample_idx = rng.choice(len(raw_radius), size=max_points, replace=False)
        raw_radius = raw_radius[sample_idx]
        raw_height = raw_height[sample_idx]

    fig.add_trace(
        go.Scattergl(
            x=raw_radius,
            y=raw_height,
            mode="markers",
            name="Data",
            marker=dict(color="rgba(0, 0, 0, 0.55)", size=2),
            hovertemplate="R: %{x:.2f} mm<br>z: %{y:.2f} nm<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=profile["radius"],
            y=profile["leveled_surface_profile"],
            mode="lines",
            name="Surface profile",
            line=dict(color="#111111", width=3),
            hovertemplate="R: %{x:.2f} mm<br>z profile: %{y:.2f} nm<extra></extra>",
        )
    )

    y_values = np.concatenate([raw_height, profile["leveled_surface_profile"]])
    y_values = y_values[np.isfinite(y_values)]
    if len(y_values):
        y_min = np.floor((np.nanmin(y_values) - 10) / 20) * 20
        y_max = np.ceil((np.nanmax(y_values) + 10) / 20) * 20
    else:
        y_min, y_max = -160, 140

    fig.update_layout(
        title=dict(
            text=(
                "ROA Surface Profile"
                f"<br><sup>Max ROA = {profile['max_roa']:.2f} nm, "
                f"Weighted mean = {profile['weighted_mean_roa']:.2f} nm, "
                f"fit = {profile['reference_fit']}</sup>"
            ),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(title="Radius (mm)", range=[0, profile["wafer_radius"]]),
        yaxis=dict(
            title="z [nm]",
            range=[y_min, y_max],
            zeroline=False,
            mirror=True,
            ticks="outside",
            showline=True,
            linecolor="black",
        ),
        yaxis2=dict(
            range=[y_min, y_max],
            overlaying="y",
            side="right",
            ticks="outside",
            showgrid=False,
            showline=True,
            linecolor="black",
        ),
        height=520,
        margin=dict(l=60, r=60, t=80, b=55),
        hovermode="closest",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            x=1.04,
            y=0.9,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="black",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#e5e5e5",
        minor=dict(showgrid=True, gridcolor="#f0f0f0"),
        mirror=True,
        ticks="outside",
        showline=True,
        linecolor="black",
    )
    fig.update_yaxes(showgrid=True, gridcolor="#e5e5e5")

    return fig


def extract_scale_from_xyz(input_path):
    """
    从XYZ文件的头部提取scale、radius和完整header信息（基于Zygo标准）

    Args:
        input_path: XYZ文件路径

    Returns:
        (scale, radius, header): 比例尺(米)、晶圆半径(米)和ZygoHeader对象的元组
    """
    from zygo_header import parse_zygo_header

    scale = None
    radius = None
    header = None

    try:
        # 使用专业的Zygo header解析器
        header = parse_zygo_header(input_path)

        if header:
            # 从header中提取scale (pixel_size)
            scale = header.pixel_size
            print(f"从文件头部读取pixel_size: {scale * 1000:.3f}mm")

            # 计算晶圆半径：phase_width 或 phase_height / 2 * pixel_size
            wafer_diameter_pixels = max(header.phase_width, header.phase_height)
            radius = (wafer_diameter_pixels / 2) * scale
            print(f"晶圆尺寸: {wafer_diameter_pixels}像素 → 半径 {radius * 1000:.3f}mm")
    except Exception as e:
        print(f"无法从文件读取参数: {e}")

    return scale, radius, header


def process_xyz(
    input_path,
    output_path,
    scale=None,
    step_x=0.0034,
    step_y=0.0005,
    slit_height=0.008,
    edge_clearance=0.05,
    sfma_threshold=7.5e-9,
    tilt_threshold=3e-6,
    pv_threshold=50e-6,
    roa_reference_radius_min=0.020,
    roa_reference_radius_max=0.100,
    roa_edge_radius_start=0.120,
    roa_bin_width=0.0005,
    roa_reference_fit="quadratic",
):
    """
    处理XYZ文件并生成分析结果

    Args:
        input_path: 输入XYZ文件路径
        output_path: 输出文件路径
        scale: 原始数据分辨率,单位米 (默认: None, 自动从文件读取)
        step_x: X方向子口径尺寸,单位米 (默认: 0.0034m = 3.4mm)
        step_y: Y方向子口径尺寸,单位米 (默认: 0.0005m = 0.5mm)
        slit_height: 调平狭缝宽度,单位米 (默认: 0.008m = 8mm)
        edge_clearance: 边缘清除量,单位米 (默认: 0.0m = 0mm, 不清除边缘)
        sfma_threshold: SFMA阈值,单位米 (默认: 7.5nm)
        tilt_threshold: 局部倾斜阈值,单位弧度 (默认: 3urad)
        pv_threshold: PV阈值,单位米 (默认: 50μm)
        roa_reference_radius_min: ROA参考区内半径,单位米 (默认: 20mm)
        roa_reference_radius_max: ROA参考区外半径,单位米 (默认: 100mm)
        roa_edge_radius_start: ROA边缘统计起始半径,单位米 (默认: 120mm)
        roa_bin_width: ROA径向bin宽度,单位米 (默认: 0.5mm)
        roa_reference_fit: ROA参考拟合类型: constant/linear/quadratic
    """
    # 如果未指定scale，尝试从文件头部读取
    radius_from_header = None  # 从文件头读取的半径
    zygo_header = None  # Zygo文件头对象
    if scale is None:
        scale, radius_from_header, zygo_header = extract_scale_from_xyz(input_path)
        if scale is None:
            # 如果无法从文件读取，使用默认值
            scale = 0.000175
            print(f"使用默认scale: {scale}m = {scale * 1000}mm")

    # print(f"Processing {input_path} -> {output_path}")
    # print(
    #     f"Parameters: scale={scale}m, step_x={step_x}m, step_y={step_y}m, slit_height={slit_height}m"
    # )

    SCALE = scale
    STEP_X = step_x
    STEP_Y = step_y

    # 使用专业的XYZfile类加载数据
    from xyzfile import XYZfile

    xyzfile_obj = XYZfile()
    if not xyzfile_obj.openFile(input_path):
        print("Error: Failed to open XYZ file!")
        return None

    # 使用getHeight()方法获取数据(已经是米为单位，NaN替换"No Data")
    height_data = xyzfile_obj.getHeight()  # shape: (height, width)

    #  转换2D数组为点云格式
    raw_data = []
    phase_origin = xyzfile_obj.getOrigin()  # (x_origin, y_origin)

    for iy in range(height_data.shape[0]):
        for ix in range(height_data.shape[1]):
            z_m = height_data[iy, ix]
            if not np.isnan(z_m):  # 跳过无效数据
                # 转换回原始像素坐标
                pixel_ix = ix + phase_origin[0]
                pixel_iy = iy + phase_origin[1]
                z_um = z_m * 1e6  # 转换回微米以保持兼容性
                raw_data.append((pixel_ix, pixel_iy, z_um))

    if len(raw_data) == 0:
        print("Error: No valid data points found in input file!")
        return None

    # 计算中心点(数据范围的中点)
    ix_values = [d[0] for d in raw_data]
    iy_values = [d[1] for d in raw_data]

    min_ix, max_ix = min(ix_values), max(ix_values)
    min_iy, max_iy = min(iy_values), max(iy_values)

    CENTER_IX = (min_ix + max_ix) / 2.0
    CENTER_IY = (min_iy + max_iy) / 2.0

    # print(f"Calculated center: CENTER_IX={CENTER_IX:.1f}, CENTER_IY={CENTER_IY:.1f}")
    # print(f"Data range: ix=[{min_ix}, {max_ix}], iy=[{min_iy}, {max_iy}]")

    # 第二遍: 转换到物理坐标并分箱
    # print("Second pass: Converting to physical coordinates and binning...")

    physical_points = []
    for ix, iy, z_um in raw_data:
        x = (ix - CENTER_IX) * SCALE
        y = (CENTER_IY - iy) * SCALE
        z_m = z_um * 1e-6
        physical_points.append((x, y, z_m))

    raw_x_arr = np.array([p[0] for p in physical_points])
    raw_y_arr = np.array([p[1] for p in physical_points])
    raw_z_arr = np.array([p[2] for p in physical_points])

    x_coords = [p[0] for p in physical_points]
    y_coords = [p[1] for p in physical_points]

    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    START_X = np.floor(min_x / STEP_X) * STEP_X
    START_Y = np.floor(min_y / STEP_Y) * STEP_Y

    # print(
    #     f"Physical bounds: x=[{min_x:.6f}, {max_x:.6f}], y=[{min_y:.6f}, {max_y:.6f}]"
    # )
    # print(f"Grid starts: START_X={START_X:.6f}, START_Y={START_Y:.6f}")

    # 数据分箱
    bins = {}
    data_count = 0

    for x, y, z_m in physical_points:
        k_x = int(round((x - START_X) / STEP_X))
        k_y = int(round((y - START_Y) / STEP_Y))
        key = (k_x, k_y)

        if key not in bins:
            bins[key] = [0.0, 0]

        bins[key][0] += z_m
        bins[key][1] += 1
        data_count += 1

    # print(f"Binned {data_count} data points into {len(bins)} bins.")

    # 应用边缘清除
    if edge_clearance > 0:
        # 计算数据的径向范围
        all_x = [START_X + k[0] * STEP_X for k in bins.keys()]
        all_y = [START_Y + k[1] * STEP_Y for k in bins.keys()]
        max_radius = max(np.sqrt(np.array(all_x) ** 2 + np.array(all_y) ** 2))

        # 将原始半径四舍五入到毫米级别，然后减去清除量
        original_radius_mm = round(max_radius * 1000)  # 转换为mm并四舍五入
        clearance_radius_mm = original_radius_mm - (edge_clearance * 1000)  # 减去清除量
        clearance_radius = clearance_radius_mm / 1000  # 转换回米

        # 过滤掉边缘区域的数据点
        filtered_bins = {}
        for key, value in bins.items():
            grid_x = START_X + key[0] * STEP_X
            grid_y = START_Y + key[1] * STEP_Y
            radius = np.sqrt(grid_x**2 + grid_y**2)
            if radius <= clearance_radius:
                filtered_bins[key] = value

        bins = filtered_bins
        print(f"原始最大半径: {original_radius_mm:.0f}mm")
        print(f"清除后半径: {clearance_radius_mm:.0f}mm")
        print(
            f"After edge clearance ({edge_clearance * 1000:.1f}mm): {len(bins)} bins remaining."
        )

    # 输出处理后的数据
    plot_x, plot_y, plot_z = [], [], []
    sorted_keys = sorted(bins.keys(), key=lambda k: (k[1], k[0]))

    with open(output_path, "w") as f:
        for k_x, k_y in sorted_keys:
            grid_x = START_X + k_x * STEP_X
            grid_y = START_Y + k_y * STEP_Y
            sum_z, count = bins[(k_x, k_y)]
            avg_z = sum_z / count

            f.write(f"{grid_x:.15f} {grid_y:.15f} {avg_z:.15f}\n")
            plot_x.append(grid_x)
            plot_y.append(grid_y)
            plot_z.append(avg_z)

    # print(f"Saved processed data to {output_path}")

    # 可视化分析
    if len(plot_x) > 0:
        x_arr = np.array(plot_x)
        y_arr = np.array(plot_y)
        z_arr = np.array(plot_z)

        # 检测晶圆标准尺寸
        wafer_radius_standard, wafer_size_inch = detect_wafer_radius(x_arr, y_arr)

        # 计算数据的实际范围（不假设是完美的圆形）
        data_max_radius = np.max(np.sqrt(x_arr**2 + y_arr**2))
        x_extent = np.max(np.abs(x_arr))  # X方向的最大范围
        y_extent = np.max(np.abs(y_arr))  # Y方向的最大范围
        data_radius = max(x_extent, y_extent)  # 数据的实际半径

        # 使用数据的实际最大半径作为晶圆半径，确保轮廓能包含所有数据点
        wafer_radius = data_max_radius

        # 使用从文件头读取的半径（如果有的话），否则使用数据计算的半径
        if radius_from_header is not None:
            # 文件头信息仅供参考，使用实际数据的最大半径
            print(f"\n晶圆尺寸信息:")
            print(f"  数据范围: X={x_extent * 1000:.1f}mm, Y={y_extent * 1000:.1f}mm")
            print(f"  数据最大半径: {data_max_radius * 1000:.1f}mm")
            print(f"  轮廓半径: {wafer_radius * 1000:.1f}mm")
            print(
                f"  轮廓直径: {wafer_radius * 2 * 1000:.1f}mm ({wafer_radius * 2 / 0.0254:.1f}英寸)"
            )
            print(f"  文件头信息: {radius_from_header * 1000:.1f}mm (仅供参考)")
            if x_extent < y_extent * 0.95:
                print(
                    f"  ⚠️  注意: X方向({x_extent * 1000:.1f}mm)小于Y方向，左右边缘可能被裁切"
                )
            print()
        else:
            print(f"\n晶圆尺寸信息:")
            print(f"  数据范围: X={x_extent * 1000:.1f}mm, Y={y_extent * 1000:.1f}mm")
            print(f"  数据最大半径: {data_max_radius * 1000:.1f}mm")
            print(f"  轮廓半径: {wafer_radius * 1000:.1f}mm")
            print(
                f"  轮廓直径: {wafer_radius * 2 * 1000:.1f}mm ({wafer_radius * 2 / 0.0254:.1f}英寸)"
            )
            if x_extent < y_extent * 0.95:
                print(
                    f"  ⚠️  注意: X方向({x_extent * 1000:.1f}mm)小于Y方向，左右边缘可能被裁切"
                )
            print()
            print()
            print(f"\n晶圆尺寸信息:")
            print(
                f"  识别尺寸: {wafer_size_inch}英寸 (标准半径: {wafer_radius_standard * 1000:.1f}mm)"
            )
            print(f"  数据范围: X={x_extent * 1000:.1f}mm, Y={y_extent * 1000:.1f}mm")
            print(f"  数据半径: {data_radius * 1000:.1f}mm")
            print(f"  轮廓半径: {wafer_radius * 1000:.1f}mm (含1.5%边距)\n")

        # 计算z_resid用于SFMA和Tilt分析
        z_resid = remove_tilt(x_arr, y_arr, z_arr)

        # 1. 去一阶面形
        z_resid, pv = calculate_surface_form(x_arr, y_arr, z_arr)
        image_path = output_path.replace(".txt", ".png")
        plot_surface_heatmap(x_arr, y_arr, z_resid, pv, image_path, wafer_radius)

        # 1.1 PV 高阈值分析
        pv_high_image_path = output_path.replace(".txt", "-pv-high.png")
        plot_high_pv_heatmap(
            x_arr, y_arr, z_resid, pv_threshold, pv_high_image_path, wafer_radius
        )

        # # 2. NCE分析 (已禁用)
        # z_nce, _, _ = calculate_nce(
        #     x_arr, y_arr, z_arr, field_size_x=0.026, field_size_y=0.008
        # )
        # valid_nce = z_nce[~np.isnan(z_nce)]
        # mean_nce = np.median(valid_nce)
        # std_raw = np.std(valid_nce)
        # mask_sigma = np.abs(valid_nce - mean_nce) <= 3 * std_raw
        # filtered_nce = valid_nce[mask_sigma]
        # std_nce = np.std(filtered_nce)
        # nce_metric = mean_nce + 3 * std_nce
        # disp_field_x = 0.026
        # disp_field_y = 0.033
        # n_disp_cols = int(np.ceil(np.max(np.abs(x_arr)) / disp_field_x))
        # n_disp_rows = int(np.ceil(np.max(np.abs(y_arr)) / disp_field_y))
        # gx = np.arange(-n_disp_cols, n_disp_cols + 1) * disp_field_x
        # gy = np.arange(-n_disp_rows, n_disp_rows + 1) * disp_field_y
        # nce_image_path = output_path.replace(".txt", "-nce.png")
        # plot_nce_heatmap(x_arr, y_arr, z_nce, std_nce, gx, gy, nce_image_path)

        # 1. SFMA分析
        z_sfma = calculate_dynamic_sfma(
            x_arr,
            y_arr,
            z_resid,
            slit_h=slit_height,
        )

        valid_sfma = z_sfma[~np.isnan(z_sfma)]
        mean_sfma = np.median(valid_sfma)
        std_sfma_raw = np.std(valid_sfma)
        filtered_sfma = valid_sfma

        std_sfma = np.std(filtered_sfma)
        sfma_metric = np.median(filtered_sfma) + 3 * std_sfma
        sfma_image_path = output_path.replace(".txt", "-sfma.png")
        plot_sfma_heatmap(
            x_arr, y_arr, z_sfma, sfma_metric, sfma_image_path, wafer_radius
        )

        # 1.1 SFMA 高阈值分析
        sfma_high_image_path = output_path.replace(".txt", "-sfma-high.png")
        plot_sfma_high_heatmap(
            x_arr, y_arr, z_sfma, sfma_threshold, sfma_high_image_path, wafer_radius
        )

        # 保存SFMA map到txt文件
        sfma_txt_path = output_path.replace(".txt", "-sfma.txt")
        with open(sfma_txt_path, "w") as f:
            for i in range(len(x_arr)):
                if not np.isnan(z_sfma[i]):
                    f.write(f"{x_arr[i]:.15f} {y_arr[i]:.15f} {z_sfma[i]:.15f}\n")

        # 2. 局部角分析
        tilt_urad = calculate_local_tilt(x_arr, y_arr, z_resid)

        valid_tilt = tilt_urad[~np.isnan(tilt_urad)]
        median_tilt = np.median(valid_tilt)
        std_tilt = np.std(valid_tilt)
        max_tilt = np.max(valid_tilt)
        tilt_metric = median_tilt + 3 * std_tilt

        tilt_image_path = output_path.replace(".txt", "-tilt.png")
        plot_tilt_heatmap(
            x_arr,
            y_arr,
            tilt_urad,
            median_tilt,
            std_tilt,
            max_tilt,
            tilt_metric,
            tilt_image_path,
            wafer_radius,
        )

        # 保存Local Tilt map到txt文件
        tilt_txt_path = output_path.replace(".txt", "-tilt.txt")
        with open(tilt_txt_path, "w") as f:
            for i in range(len(x_arr)):
                if not np.isnan(tilt_urad[i]):
                    f.write(f"{x_arr[i]:.15f} {y_arr[i]:.15f} {tilt_urad[i]:.15f}\n")

        # 3. 局部倾斜角度分析 (>阈值)
        high_tilt_image_path = output_path.replace(".txt", "-tilt-high.png")
        # tilt_threshold is in radians, convert to urad for display if needed inside function?
        # plot_high_tilt_heatmap expects threshold in urad (based on previous hardcoded 12.5)
        # Wait, let's check plot_high_tilt_heatmap implementation.
        # It takes tilt_urad and threshold. tilt_urad is in urad.
        # So we need to pass threshold in urad.
        plot_high_tilt_heatmap(
            x_arr,
            y_arr,
            tilt_urad,
            tilt_threshold * 1e6,
            high_tilt_image_path,
            wafer_radius,
        )

        # --- Plotly Figure Generation ---
        figures = {}

        # 1. Surface Form (PV)
        figures["pv"] = generate_plotly_heatmap(
            x_arr,
            y_arr,
            z_resid,
            "去一阶面形",
            f"PV = {pv * 1e6:.2f} um",
            wafer_radius,
            z_label="m",
        )

        # 1.1 PV High
        mask_pv = (~np.isnan(z_resid)) & (np.abs(z_resid) > pv_threshold)
        figures["pv_high"] = generate_plotly_scatter(
            x_arr[mask_pv],
            y_arr[mask_pv],
            z_resid[mask_pv],
            f"去一阶面形 (> {pv_threshold * 1e6:.1f} μm)",
            circle_radius=wafer_radius,
            z_label="m",
        )
        if np.nansum(mask_pv) == 0:
            figures["pv_high"].add_annotation(
                text=f"No data > {pv_threshold * 1e6:.1f} μm",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        # 2. SFMA
        figures["sfma"] = generate_plotly_heatmap(
            x_arr,
            y_arr,
            z_sfma,
            "SFMA",
            f"m3s = {sfma_metric * 1e9:.2f} nm",
            wafer_radius,
            z_label="m",
        )

        # 2.1 SFMA High
        mask_sfma = (~np.isnan(z_sfma)) & (np.abs(z_sfma) > sfma_threshold)
        figures["sfma_high"] = generate_plotly_scatter(
            x_arr[mask_sfma],
            y_arr[mask_sfma],
            z_sfma[mask_sfma],
            f"SFMA (> {sfma_threshold * 1e9:.1f} nm)",
            circle_radius=wafer_radius,
            z_label="m",
        )
        if np.nansum(mask_sfma) == 0:
            figures["sfma_high"].add_annotation(
                text=f"No data > {sfma_threshold * 1e9:.1f} nm",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        # 3. Tilt
        figures["tilt"] = generate_plotly_heatmap(
            x_arr,
            y_arr,
            tilt_urad,
            "局部角分布",
            f"max= {max_tilt:.2f} μrad, m3s = {tilt_metric:.2f} μrad",
            wafer_radius,
            z_label="μrad",
        )

        # 3.1 Tilt High
        # Note: tilt_threshold input is in radians, plot expects check against urad if converted?
        # In logic above (lines 1030+), it calls plot_high_tilt_heatmap with threshold * 1e6.
        # But tilt_urad is already in urad.
        # So we compare tilt_urad > tilt_threshold * 1e6
        thresh_urad = tilt_threshold * 1e6
        mask_tilt = (~np.isnan(tilt_urad)) & (tilt_urad > thresh_urad)

        figures["tilt_high"] = generate_plotly_scatter(
            x_arr[mask_tilt],
            y_arr[mask_tilt],
            tilt_urad[mask_tilt],
            f"局部角分布 (大于{thresh_urad}μrad区域)",
            circle_radius=wafer_radius,
            z_label="μrad",
        )
        if np.nansum(mask_tilt) == 0:
            figures["tilt_high"].add_annotation(
                text=f"No data > {thresh_urad} μrad",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )

        roa_z_arr = remove_tilt(raw_x_arr, raw_y_arr, raw_z_arr)
        roa_profile = calculate_roa_profile(
            raw_x_arr,
            raw_y_arr,
            roa_z_arr,
            reference_radius_min=roa_reference_radius_min,
            reference_radius_max=roa_reference_radius_max,
            edge_radius_start=roa_edge_radius_start,
            wafer_radius=np.nanmax(np.sqrt(raw_x_arr**2 + raw_y_arr**2)),
            bin_width=roa_bin_width,
            reference_fit=roa_reference_fit,
        )
        if roa_profile is not None:
            figures["roa"] = generate_roa_figure(roa_profile)

        return {
            "pv": pv,
            "sfma": sfma_metric,
            "tilt": tilt_metric,
            "roa_max": roa_profile["max_roa"] if roa_profile is not None else np.nan,
            "roa_weighted_mean": (
                roa_profile["weighted_mean_roa"] if roa_profile is not None else np.nan
            ),
            "roa_p99": roa_profile["p99_roa"] if roa_profile is not None else np.nan,
            "figures": figures,
        }


if __name__ == "__main__":
    process_xyz("example/005-avg.xyz", "output/005-avg-processed.txt")
