# deepcomp

一个很小的深度图像（deep image）工具包。`.deep` 文件的读写、`probe`，以及合成（merge / holdout / Cryptomatte 隔离 / flatten）都已实现，只用标准库。

```bash
python -m deepcomp probe --input fixtures/hero.deep
python -m deepcomp probe --input fixtures/backdrop.deep --manifest fixtures/crypto_manifest.json

python -m deepcomp composite \
  --inputs fixtures/hero.deep fixtures/backdrop.deep \
  --holdout fixtures/holdout.deep \
  --isolate hero \
  --out-deep merged.deep --flatten merged.flat --preview merged.ppm \
  --report report.json --manifest fixtures/crypto_manifest.json
```

格式和合成约定见 `docs/`。夹具说明见 `fixtures/catalog.md`。

不要把密钥或 `.env` 提交进仓库。不要用 Docker。
