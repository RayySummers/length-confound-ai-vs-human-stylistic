# O'Sullivan (2025) 精读笔记

O'Sullivan, James. (2025). Stylometric comparisons of human versus AI-generated creative writing. *Humanities and Social Sciences Communications*, 12, 1708. DOI: 10.1057/s41599-025-05986-3.

依据 nature.com 的开放获取 PDF，全文 6 页。下面的页码指 PDF 页码。引号里是原文。

一句话：三个模型的文本各自紧密成簇，人类文本更分散，作者据此判断 AI 风格仍可区分。但全文没有数值结果，也没有控制文本长度。

## 1. 研究问题

主问题写在结论里：LLM 能不能写出在统计上与人类无法区分的创意散文。作者的回答是 "The answer is no, at least, not yet."（第 5 页）

具体问两件事。人类与 AI 的创意短篇能不能用计量文体学区分。两类文本会不会各自聚成簇。（摘要，第 1 页）

作者认为前人漏了两点。已有研究用计量文体学比较人与 LLM（Zaitsu and Jin, 2023; Opara, 2024; Wang et al., 2024; Przystalski et al., 2024），但 "none have looked at explicitly literary texts, nor have they applied Burrows' Delta"（第 2 页）。新意落在两点：明确是文学文本；用 Burrows' Delta。

作者的立场是把"文学性"和"复杂度"的主观判断拿掉，只看形式特征。它把风格定义成词频里能测出来的作者指纹。（第 2 页）

## 2. 语料

数据来自 Nina Beguš (2024) 的公开语料，放在 OSF，DOI 10.17605/OSF.IO/K6FH7。（第 2 页；第 5 页）

构成如下（第 2 页）：

- 250 篇人类短篇，Amazon Mechanical Turk 众包。
- 80 篇由 OpenAI 的 GPT-3.5 与 GPT-4 生成。
- 50 篇由 Meta 的 Llama 3-70b 生成。

三项相加是 380 篇。作者没有单独写出分析样本量，只说用了 "the complete Beguš corpus"，也没有写 GPT-3.5 与 GPT-4 各多少篇。380 是三项相加得来的，不是文中单独给出的数字。引用时要注意这一点。

体裁是短篇虚构，prompt 用英文写。两个 "please continue the story" prompt，都围绕人造人（第 2 页）：

1. 一个人造了人造人。后来这个创造者爱上了它。
2. 一个人造了人造人。另一个人爱上了它。

题材来自 Beguš 对"Pygmalionesque"与"agalmatophiliac"两类故事的分法。（第 2 页）

人类写作者被要求写 150–500 词。（第 2 页）模型输出是否也受这个字数限制，文中没有说。模型输出的实际长度也没有报告。

摘要称这是 "balanced dataset"（第 1 页）。实际是 250 对 130，人类文本接近 AI 的两倍。第 2 页的 "balanced representation" 说的是模型之间有代表性，不是人与 AI 之间均衡。两处说的不是一回事。

## 3. 方法

用的是 Burrows' Delta，NLTK 写的 Python 脚本，代码在作者 GitHub（O'Sullivan, 2024）。（第 3 页；第 5–6 页）

**词表。** 100 个高频词（100 MFW）。（第 3 页）作者的理由是高频词多为功能词，受内容影响小，也不容易被作者有意改动。它引 Hoover (2009, 35) 说明功能词占文本词量的大头，频率稳定。（第 4 页）

**距离。** 先算每个 MFW 在每篇文本里的频率，再用 z 分数标准化。Delta 是两篇文本这 100 个 z 分数的平均绝对差。值越小，风格越近。（第 2 页）

z 分数的用途，作者的原话是 "standardise the data to account for differences in text length and variability"。（第 2 页）这一句是理解它长度处理的关键。

**聚类。** 先算成对距离矩阵，再做层次聚类，连接方式用平均连接（average linkage）。作者说平均连接在"簇够紧"和"避免链式效应"之间比较平衡。（第 3 页）结果画成树状图，即图 1。（第 3 页）

**降维。** 用多维标度（MDS）把距离矩阵压到二维，画散点图，即图 2。（第 3 页；图 2 在第 4 页）文中没有写是经典 MDS 还是序数 MDS，也没有报告 stress。

**有意排除的指标。** 句长、句法复杂度、标点，都不在分析里。作者的原话是 "This study deliberately excludes explicit measures of sentence length, syntactic complexity, and punctuation patterns."（第 2 页）

**没有采用的长度稳健变体。** 作者提到 Cosine Delta 受文本长度与尺度变化的影响更小（Jannidis et al., 2015），但分析仍用 Burrows' Delta。（第 2 页）

**没交代的预处理。** 分词规则、大小写、标点是否保留、是否词形还原、是否做 culling（剔除低频词）、MFW 词表是在合并语料上排还是分语料排、z 分数的均值和标准差按什么范围算，正文都没有写。脚本在 GitHub，正文没有说明。

**没有统计检验。** 这项分析里没有显著性检验，没有分类器，没有报告任何 Delta 数值。所有结论来自对两张图的阅读。

## 4. 结论

结果都是定性的，靠图 1 和图 2 说话。

簇的结构（第 4 页）：

- 同一模型的文本紧密聚在一起。
- 三个模型各自成簇，合起来又形成一个更大的"生成式 AI"类，与人类文本分开。
- 人类文本的簇更宽，也更松散。
- GPT-4 比 GPT-3.5 更紧。
- Llama 70b 同样紧密。

簇宽与簇间距的差别，文中只有文字和图形，没有数字。簇宽上，人类组更宽；簇间距上，作者只说 LLM 簇的位置与人类不同。没有 Delta 均值，没有簇内距离，没有簇间距离，没有轮廓系数，也没有 MDS 的 stress。图 1 的纵轴是 Delta 距离，但正文没有引用其中任何数值。

MDS 图里，人类点分布得更散，模型点更集中，LLM 簇相对人类文本的位置也不同。（第 5 页）作者据此说人类写作即便在固定 prompt 下仍保留个体性。

少数 GPT-3.5 文本落在人类簇内或附近。作者称这类重叠是 "exceptions rather than the norm"。（第 5 页）它认为这可能与 GPT-3.5 不如 GPT-4 精细有关，输出变异更大。

作者对人类更宽的解释有三点：个体写作风格不同；创作水平不同；对 prompt 的投入不同。人会加入个人化的笔触。（第 4 页）

作者对 AI 更紧的解释：模型优化的是连贯与流畅，不是多样。（第 5 页）GPT-4 更紧，作者认为这可能是训练数据与架构改进的结果，它能更稳定地跟随 prompt，输出也更贴近训练分布。（第 4 页）

总体判断还是那句 "The answer is no, at least, not yet."（第 5 页）

作者另外用了一整段警告：不要把计量文体学当成学术诚信的执法工具。它认为这种方法在语料层面稳健，在单个学生身上不适用。（第 5 页）

## 5. 局限

### 5.1 作者承认的

1. 固定 prompt 限制了创作空间，可能把人和模型都推向特定的叙事结构与风格。（第 3 页）
2. MTurk 的人类文本质量和对 prompt 的遵循程度不一。"contrived" 的文本未必算真正的"文学"。（第 3 页）
3. 数据集是受控的，结论不宜过度解读。后续需要更大的数据集、不同的 prompt、更新的模型（包括 GPT-5），还需要定性分析配合。（第 5 页）
4. 方法不适合用来判定学术诚信。（第 5 页）

### 5.2 我看出来的

**1. 长度没有控制。这是最要紧的一条。**

作者只做了 z 分数标准化，并说这能处理长度差异。（第 2 页）除此之外，全文没有给出任何文本长度的描述统计，没有做长度匹配，没有把长度当协变量，也没有按长度分层。

人类文本被限制在 150–500 词（第 2 页）。模型的输出长度未知。两组的长度分布本来就可能不一样。

作者自己提到 Cosine Delta 对长度变化更不敏感，却没有用它。（第 2 页）

后果落在簇宽上。簇宽量的是离散程度。文本越短，高频词的频率估计越不稳定，点就越容易散。人类文本被要求在 150–500 词之间，模型的长度没有报告。如果两组长度不同，簇宽就会跟着不同，而作者没有办法把这一部分从风格里分出来。人类组更宽，可能有一部分只是长度造成的，不全是风格。这个推断不需要重跑分析就能提出，但要证实需要长度信息，而文中没有。

**2. 没有数值结果。** 没有 Delta 值，没有检验，没有置信区间，没有分类准确率。结论全靠两张图。图 2 是二维投影，没有 stress，二维图上的距离不能当原始 Delta 用。

**3. 100 个高频词没有依据。** 为什么是 100，不是 50 或 200，文中没说。也没有敏感性分析。作者引了 Evert et al. (2017) 比较不同 Delta 变体，但正文没有说明是否据此选参数。（第 2 页）

**4. 语料构成不清。** 250 对 130，不平衡。GPT-3.5 与 GPT-4 各多少篇没写。分析样本量也没有单独写出。

**5. 生成参数没写。** 温度、采样方式、每个 prompt 生成几篇，都没有。同模型文本相似，可能来自同一个 prompt 或同一套解码参数，不一定是模型风格。

**6. 采集条件不同。** 人类在 MTurk 上完成写作任务，模型文本由模型生成。两边的写作条件不同，这些差异也会进距离矩阵。

**7. 单一题材。** 两个 prompt 都是人造人恋爱故事。结论不能推到其他体裁。

**8. 聚类参数没有稳健性检验。** 只报了一种距离、一种连接方式。换 linkage、换 Delta 变体、换 MFW 数量，簇形可能变。

**9. 图 2 中心区域的重叠看起来不止 GPT-3.5。** 作者只提 GPT-3.5 的少量越界（第 5 页）。二维图的中心区域，人类点与模型点混在一起。二维投影会压缩距离，不能据此推翻结论。但这至少提示，"清晰分离"主要是靠人类组的离散度撑起来的，不是两组各占一块互不重叠的区域。

## 附：与本项目现有表述的出入

这部分不是原文的局限，是引用时要注意的地方。

1. `proposal_v14.md:17` 写 "recent applications of stylometry reach high accuracy in distinguishing human from AI creative writing (O'Sullivan, 2025)"。`proposal_v14_zh.md:17` 写"能达到较高准确率"。原文没有报告任何准确率，也没有训练分类器。它报告的是聚类结果。建议改成："O'Sullivan (2025) 用 Burrows' Delta 加层次聚类与 MDS，发现人类文本的簇比模型文本更宽，三个模型各自成簇，AI 文本整体与人类分开（第 4 页）。"

2. `docs/literature-review.md:51` 说它 "demonstrating that this simple, interpretable metric can effectively separate the two categories"，还说它 "supports H5 (classifier accuracy >70%)"。后半句没有依据。`docs/literature-review.md:69` 把它与 Breithaupt 并列，说两者都 "demonstrate that stylometric features alone can achieve high classification accuracy"，同样没有依据。

3. 期刊名应为 "Humanities and Social Sciences Communications"。`docs/literature-review.md:51` 和 `docs/literature-review.md:82` 写成 "Nature Humanities and Social Sciences Communications"。Nature Portfolio 是出版方，刊名里没有 Nature。

4. `docs/literature-review.md:51` 说它支持 H3（TTR）。原文没有做 TTR。它只用 100 个高频词的分布。这个推断可以留，但要写成推断，不能说成它的发现。
