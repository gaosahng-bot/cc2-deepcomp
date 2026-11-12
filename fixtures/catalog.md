# 夹具说明

全部是 8×8 的 DCP1 文件，颜色已预乘。crypto 名称和 id 在 `crypto_manifest.json`。

| 文件 | 内容 |
|---|---|
| `backdrop.deep` | 每个像素一条表面样本，z=10，预乘 RGB=(0, 0, 0.4)，A=1，名字 `backdrop`。 |
| `hero.deep` | 只在像素 x∈[2,5]、y∈[2,5] 有样本：表面 z=2，RGB=(0.8, 0.1, 0.0)，A=0.9，名字 `hero`。其余像素为空。 |
| `fog.deep` | 只在 y∈[3,4] 的整行有体积样本：z∈[1.5, 4.0]，RGB=(0, 0.45, 0.15)，A=0.6，名字 `fog`。这段体积会穿过 hero 的深度。 |
| `holdout.deep` | 与 hero 同一批像素、同一深度 z=2，不透明白色，名字 `holdout_card`。只应被当作 holdout，不应当颜色。 |
| `overlap.deep` | 两个手工像素。`(1,1)` 有两条相交体积：hero 的 `[1,3]`（RGB=A 为 0.5 红）和 fog 的 `[2,4]`（0.5 蓝）。`(4,1)` 是 coverage=0.5 的红色表面（未乘 coverage 前 RGB=A 为 0.8）叠在 z=5 的 backdrop 表面上。`(6,6)` 为空。 |

实现时请按字节内容处理，不要对文件名写死答案。正式验收还会用未放进仓库的图。
