"""教学版：两条相关 ROC 的全 AUC 和配对 DeLong 检验，Python 3.8+。"""
from math import erfc, isfinite, sqrt
from statistics import NormalDist, mean, variance

EXAMPLE = [
    ("P1", 1, .90, .95), ("P2", 1, .80, .65),
    ("P3", 1, .60, .45), ("P4", 1, .40, .35),
    ("N1", 0, .70, .85), ("N2", 0, .50, .55),
    ("N3", 0, .30, .25), ("N4", 0, .20, .15),
]


def paired_delong(rows, conf_level=.95):
    """每行：(唯一受试者 ID, 0/1 真实标签, A 分数, B 分数)。高分偏阳性。"""
    rows = list(rows)
    if not 0 < conf_level < 1:
        raise ValueError("置信水平必须在 0 和 1 之间")
    ids = [i for i, _, _, _ in rows]
    if any(i is None or i == "" for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("ID 不能缺失或重复；先按受试者 ID 对齐两个模型")
    if any(y not in (0, 1) or not isfinite(a) or not isfinite(b)
           for _, y, a, b in rows):
        raise ValueError("标签必须为 0/1，分数必须有限且不能缺失")
    pos = [(a, b) for _, y, a, b in rows if y == 1]
    neg = [(a, b) for _, y, a, b in rows if y == 0]
    m, n = len(pos), len(neg)
    if min(m, n) < 2:
        raise ValueError("至少要有 2 个阳性和 2 个阴性才可估计样本方差；这不是充分样本量")

    def win(x, y):
        return 1.0 if x > y else 0.5 if x == y else 0.0

    auc = [0.0, 0.0]
    positive_diff = [0.0] * m
    negative_diff = [0.0] * n
    for i, (pa, pb) in enumerate(pos):
        for j, (na, nb) in enumerate(neg):
            wa, wb = win(pa, na), win(pb, nb)
            auc[0] += wa
            auc[1] += wb
            positive_diff[i] += wa - wb
            negative_diff[j] += wa - wb

    auc_a, auc_b = (x / (m * n) for x in auc)
    delta = mean(positive_diff) / n
    var = variance(x / n for x in positive_diff) / m + variance(
        x / m for x in negative_diff) / n
    if var <= 0:
        raise ValueError("差值方差为零，常规 DeLong 正态检验不可用；请检查样本与分数")
    se = sqrt(var)
    z = delta / se
    p_two_sided = erfc(abs(z) / sqrt(2))
    q = NormalDist().inv_cdf(1 - (1 - conf_level) / 2)
    return {
        "auc_A": auc_a, "auc_B": auc_b, "delta_A_minus_B": delta,
        "se": se, "z": z, "p_two_sided": p_two_sided,
        "ci_low": delta - q * se, "ci_high": delta + q * se,
    }


if __name__ == "__main__":
    for field, value in paired_delong(EXAMPLE).items():
        print(f"{field:17s} {value:.6f}")
