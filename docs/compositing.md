# 合成约定

实现必须遵守这些规则。夹具是按这些规则生成的，不要改成“看起来差不多”的经验混合。

## 有效颜色

一条样本在参与运算前，先把 coverage 打进去：

```
rgb = (r, g, b) * coverage
alpha = a * coverage
```

夹具里 coverage 都是 1.0，但实现不要写死。

## 体积切分

体积样本满足 `zfront < zback`，颜色沿区间按均匀介质处理。若要在区间内的 `z*` 处切开（`zfront < z* < zback`）：

```
t = (z* - zfront) / (zback - zfront)
alpha_front = 1 - (1 - alpha) ** t
```

- 前半段 `[zfront, z*]`：alpha 为 `alpha_front`；若原来 alpha > 0，则 `rgb_front = rgb * (alpha_front / alpha)`，否则 rgb 为 0。coverage 已经在上一步打进 rgb/alpha，切分时不再改 coverage。
- 后半段 `[z*, zback]`：`t_back = 1 - t`，同样公式。
- `crypto_id` 原样保留。

切分不得改变“整段重建”后的结果：同一条体积样本在没有其它东西插入时，切一刀再从前到后合成，应回到原来的 rgb/alpha。

## 合并（merge）

把多张深度图按像素叠在一起，得到一张新的深度图：

- 只并入颜色层样本（见下面的 isolate / holdout）。
- 每个像素的样本按 `(zfront, zback, 输入序号, 原顺序)` 排序，输入序号就是命令行里 `--inputs` 的顺序，靠前的更优先。
- 收集该像素所有样本的 zfront/zback 作为切分边界，把跨边界的体积样本切开，再写入结果。表面样本（`zfront == zback`）不切。
- 结果里每条样本的 coverage 写成 1.0，rgb/alpha 写成已经乘过 coverage、并且切分后的值。

## Holdout

`--holdout` 指定的图只提供遮挡，不往结果里加颜色。flatten 时把 holdout 样本看成 `rgb = (0, 0, 0)`、alpha 仍按上面规则计算，并按同样的 Z 排序和体积切分插入序列。holdout 样本不要写进 `--out-deep`。

同一深度区间内的次序：先放 holdout 样本（只挡光、不加颜色），再按 `--inputs` 的顺序放颜色样本。因此和 holdout 同深度的颜色会被挡住。

## 从前到后 flatten

对每个像素，把（切分并排序后的）样本按顺序合成到 2D：

```
acc_rgb = (0, 0, 0)
acc_a = 0
for sample in samples:
    pass_through = 1 - acc_a
    acc_rgb += sample.rgb * pass_through
    acc_a += sample.alpha * pass_through
```

holdout 样本只增加 `acc_a`（以及因此削弱后面的颜色），不增加 `acc_rgb`。

输出 `.flat` 的像素是预乘 RGBA。若 `acc_a` 因浮点略超 1，写入前把 alpha 夹到 `[0, 1]`，rgb 只在明显的超量（比如某个通道 > 1 + 1e-5）时才按通道夹到 `[0, 1]`；正常预乘结果不要随便做伽马。

## Cryptomatte 隔离

`--isolate NAME` 用 `deepcomp.crypto_hash.crypto_id(NAME)` 得到目标 id。

- 颜色层里 id 不匹配的样本丢弃，不进入 `--out-deep`，也不在 flatten 里当颜色。
- holdout 不受 isolate 过滤，仍然全部参与遮挡。
- 名字必须和 manifest 里一致（大小写敏感）。未知名字按“没有任何颜色样本命中”处理，不要崩溃。

## `.flat` 输出

64 字节头 + `width*height*4` 个 little-endian f32，行优先，每像素 RGBA：

- 魔数 `FLT1`
- u16 版本 = 1
- u16 width
- u16 height
- 其余头字节为 0

可选 `--preview out.ppm`：把预乘 RGB 转非预乘后再量化。`A <= 1e-6` 的像素写成黑；否则 `display = rgb / A`，每个通道 `round(clamp(display, 0, 1) * 255)`，写成二进制 PPM（P6）。
