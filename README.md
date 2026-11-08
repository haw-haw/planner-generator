# planner-generator

一个用 Python 生成可打印手帐（A5 / A6 两种尺寸，骑马钉打印版）的工具。
当前版本生成 **2027 年手帐**；修改 `generate.py` 顶部的 `YEAR` 常量即可生成其他年份。

## 成品文件

| 文件 | 用途 |
| --- | --- |
| `output/planner-2027-A4-booklet.pdf` | **A5 手帐，用 A4 纸打印**：每张 A4 两面共 4 个 A5 页面，44 个 PDF 页面 = 22 张纸 |
| `output/planner-2027-A5.pdf` | A5 手帐按阅读顺序排列的单页版，用于屏幕预览或打印机的"小册子"功能 |
| `output/planner-2027-A5-booklet.pdf` | **A6 手帐，用 A5 纸打印**：每张 A5 两面共 4 个 A6 页面，44 个 PDF 页面 = 22 张纸 |
| `output/planner-2027-A6.pdf` | A6 手帐按阅读顺序排列的单页版 |
| `output/planner-2027-A4-folded.pdf` | A5 手帐，用 A4 纸打印，**单张对折**版：每张纸是连续的 4 页 |
| `output/planner-2027-A5-folded.pdf` | A6 手帐，用 A5 纸打印，**单张对折**版：每张纸是连续的 4 页 |

`*-booklet.pdf` 与 `*-folded.pdf` 内容相同，区别只在装订方式：

- **booklet（骑马钉）**：所有纸叠在一起整叠对折，折线上订钉。最外面一张是第 1、2、87、88 页。结实、能摊平。
- **folded（单张对折）**：每张纸单独对折后按顺序叠放，第 1 张是第 1–4 页，第 2 张是第 5–8 页，以此类推。
  折线处是书脊，可用书夹/长尾夹、书脊涂胶、侧边订钉，或打孔放进活页夹；方便增删、按季度分册。

两种尺寸内容相同（各 88 页）：

- 封面、个人信息 + 年度目标、2027 年历
- 每月一个跨页：左页月历（农历、节气、节日、法定节假日），右页目标 / 待办 / 习惯打卡 / 月末回顾
- 每周一页（周一开始）：7 天格子 + 本周重点
- 2028 年历、点阵笔记页、封底

A6 版为了保证可读性和书写空间，每页的行数比 A5 版略少，书写行距 5 mm（A5 版 6 mm）。

## 打印与装订

1. 打开对应的 `*-booklet.pdf`，纸张选打印用纸（A5 手帐选 A4，A6 手帐选 A5），
   方向 **横向**，缩放 **100%**（不要"适合页面"）。
2. 双面打印，选择 **短边翻转**（Short Edge）。建议先只打印第 1–2 页确认正反面方向。
3. 打印完成后（打印前纸张无需任何处理）：
   - booklet：22 张纸按出纸顺序叠好，整叠从中间对折，在折线上订 2 个钉。需要长臂订书机；没有的话，
     可以把普通订书机打开，从内页折线处把钉打进垫在下面的橡皮/泡沫上，再用手把钉脚掰平。
   - folded：每张纸单独对折（封面那面朝外），按出纸顺序叠放，再按需要装订。

不需要裁剪。纸叠较厚时，内页在开口边会略微凸出约 1–2 mm，介意的话可以用美工刀和直尺修齐。

## 重新生成

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python generate.py        # both sizes
.venv/bin/python generate.py a6     # only one size
.venv/bin/python generate.py --impose-only   # re-impose from existing single-page PDFs
```

需要本机安装 Google Chrome（用于 HTML 转 PDF），可用环境变量 `CHROME` 指定路径。
A6 的样式在 `style-a6.css`（覆盖 `style.css`），页面尺寸参数在 `generate.py` 的 `FORMATS` 中，两处需保持一致。

### 更新放假调休

国务院 2027 年放假安排公布前，`holidays.json` 只列出了法定节日当天。通知公布后，把放假日期填进 `off`、
补班日期填进 `work`，重新运行 `generate.py` 即可。
