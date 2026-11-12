# deepcomp

一个很小的深度图像（deep image）工具包雏形。`.deep` 文件的读写和 `probe` 已经能用，合成、holdout 和 Cryptomatte 隔离还没做。

```bash
python -m deepcomp probe --input fixtures/hero.deep
python -m deepcomp probe --input fixtures/backdrop.deep --manifest fixtures/crypto_manifest.json
```

格式和合成约定见 `docs/`。夹具说明见 `fixtures/catalog.md`。

不要把密钥或 `.env` 提交进仓库。不要用 Docker。
