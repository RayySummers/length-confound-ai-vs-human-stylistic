# MTLD 小节压缩 diff
2026-10-17 · 基线＝压缩前

改动：删除独立小节「MTLD Dominance and Text Length」／「MTLD 的主导地位与文本长度」（含 title 与五段）；内容压缩为一段，并入「Vocabulary Diversity as the Dominant Classifier Feature」／「词汇多样性作为分类器的主导特征」小节。保留的要点：词数加入后准确率 95.7%、词数 28.1%、MTLD 34.0%→29.4%；无 MTLD 七特征 91.0%；长度匹配子样本 34.8% 但无定论；条件层面相关 3/10 显著、TTR |r|=0.446；结论＝部分解释、留待 N=90。

---

## EN

--- proposal_v14.md.bak-mtld-pre	2026-10-17 15:33:12.989983189 +0800
+++ proposal_v14.md	2026-10-17 15:34:00.403056710 +0800
@@ -299,23 +299,14 @@
 
 MTLD (with the corrected lexical_diversity reference values, where human mean is 13.3 and AI means range 14.3-15.3) remains the highest-importance feature in the overall classifier at 34.0% of feature importance, although its univariate discriminating power is limited by the narrow between-condition variance of the reference values (about 0.4 across conditions). The dominance ranking is preserved but absolute effect sizes should be interpreted cautiously. This finding is notable because H3 (TTR) showed raw group differences in only 5 of 9 conditions (4 of 9 after length control, direction reversed), yet MTLD is the most powerful discriminator in the multivariate framework. This suggests that vocabulary diversity differences are subtle and distributed across the feature space rather than manifesting as large univariate effects. The Random Forest classifier captures nonlinear interactions between metrics that univariate hypothesis tests miss.
 
+
+MTLD's prominence as a discriminator invites one further question: how much of it is text length? Adding word count as a ninth feature raises accuracy to 95.7% and makes word count the second most important feature (28.1%), while MTLD falls from 34.0% to 29.4%, indicating substantial shared variance between length and MTLD; a classifier trained without MTLD still reaches 91.0% raw accuracy, about one point above the majority-class baseline. A length-matched subsample (400-800 words; 12 human and 212 AI texts) leaves MTLD the top feature (34.8%) but is inconclusive on accuracy, and condition-level correlations between MTLD and length are significant in only 3 of 10 conditions, with TTR the more length-dependent measure (mean |r| = 0.446). The conservative reading is that MTLD's dominance is partially, but not fully, explained by length; residualization at N=90 is required to separate the two.
 ### Lexical Diversity: Direction Conflict and the MTLD Variance Anomaly
 
 The three lexical-diversity metrics point in different directions at the group level. TTR indicates that AI texts are *less* lexically diverse (lower TTR; median d = −0.42, significant in 5/9), whereas MATTR (window 100) and MTLD indicate that AI texts are *more* diverse (median d = +1.66 and +2.03; significant in 9/9). This is the length confound of this report in miniature: TTR is strongly length-dependent (r ≈ −0.54 between TTR and word count across the sample), and AI texts here are ~1.6× longer than human texts, so a direction reversal in TTR is expected; MATTR and MTLD show much weaker length associations (r ≈ +0.22 and +0.12 respectively). Consistent with this, length control largely resolves the conflict: the raw AI-lower TTR differences do not survive as such, and the surviving residualized differences (4/9) reverse to AI > human — aligning TTR with MATTR and MTLD (§3.2). We report the conflict and its length-shaped resolution explicitly; the planned N=90 replication should adjudicate it formally.
 
 A second anomaly concerns MTLD's *variance* structure: it is the only metric for which the AI groups' within-model variance exceeds the human group's (median variance ratio 2.40; smaller in just 1/9 models), while showing the largest mean-difference effects (median d = +2.03). No other metric shows this mean-vs-variance dissociation. Possible mechanisms — the segment-threshold construction of MTLD, residual length effects, or genuine cross-model variation — are left open for the N=90 replication. Accordingly, MTLD should not be treated as the report's strongest discriminator (see also the classifier caveats below).
 
-### MTLD Dominance and Text Length
-
-A critical concern is whether MTLD's 34.0% feature importance reflects genuine vocabulary diversity differences or merely correlates with text length. AI-generated texts are consistently longer than human texts in this dataset (Table 1): mean word counts range from 531 (GPT-3.5) to 878 (Muse-Spark) compared to 439 for human texts, and AI texts show far less within-condition length variation (SD 28-116 words) than human texts (SD 245 words). Since MTLD (with the corrected lexical_diversity values, where variance is small across conditions) is less likely to be confounded by text length than the original custom implementation suggesteds independently of lexical diversity.
-
-Three pieces of evidence address this concern. First, between-condition length differences are large (human 439 ± 245 words vs AI 531-878 words; mean AI length 1.4× human mean); the classifier operates on between-condition variance, so within-condition correlation is not the relevant defense. We add word count as a 9th feature (see below) to quantify length's incremental contribution directly, with only 3 of 10 conditions showing significant correlations (Human r=+0.67, p<0.001; Claude r=+0.44, p=0.016; Muse-Spark r=+0.43, p=0.019). Notably, GPT-3.5 shows a negative, non-significant correlation (r=-0.14, p=0.47), suggesting that length does not uniformly drive MTLD across conditions. TTR, by contrast, shows stronger length dependence (mean |r|=0.446, significant in 6 of 10 conditions), confirming the known mathematical relationship between text length and type-token ratios.
-
-Second, a length-matched subsample analysis (restricting to texts of 400–800 words, retaining 12/30 human samples and 212/269 AI samples) yields two key results: (a) the Random Forest classifier achieves 94.2% ± 2.0% raw accuracy — which is below the 94.6% majority-class baseline (12/(12+212)) in this subsample (12 human + 212 AI). The 94.2% raw accuracy is below the majority-class baseline, and n=12 humans provides insufficient power for reliable balanced-accuracy estimates; this subsample analysis is inconclusive on whether MTLD's discriminating power is independent of text length. The question is deferred to the N=90 residualization-based analysis (Future Work). (b) MTLD retains 34.8% feature importance in the subsample, but given the inconclusive overall accuracy, this finding is suggestive rather than definitive.
-
-Third, when word count is added as a ninth feature to the classifier, accuracy rises to 95.7% and word count itself becomes the second most important feature (28.1%) behind MTLD (29.4%); MTLD declines from 34.0% to 29.4% (a 4.6 pp drop), while word count absorbs 28.1% of importance, indicating substantial shared variance between length and MTLD. A classifier trained without MTLD (using the other 7 features only) still achieves 91.0% raw accuracy (about 1 percentage point above the 90.0% majority-class baseline), suggesting that the remaining features may carry non-trivial signal independently. Balanced accuracy for the no-MTLD ablation is not reported here as it requires re-running the StratifiedGroupKFold pipeline without the MTLD feature; this is deferred to the supplementary materials.
-
-The most conservative interpretation is that MTLD dominance is partially but not fully explained by length. Approximately 28% of the total feature importance is captured by word count, though this shares substantial variance with MTLD (correlation analysis §4); the discriminating-power attribution requires residualization analysis at N=90. MTLD's discriminating power, while still significant in the multivariate classifier, is partially confounded with text length; the residualization-based adjudication is deferred to N=90 (Future Work). With the corrected lexical_diversity values and the length-control analysis, the MTLD-direction-vs-TTR-direction consistency is resolved: after length control, TTR's surviving differences reverse to AI > human, aligning with MATTR and MTLD (§3.2, §4). Future work at N=90 should formally control for length through regression-based approaches (e.g., residualized MTLD after regressing on word count) or exact length-matching designs.
 
 ## 5. Conclusion
 


---

## ZH

--- proposal_v14_zh.md.bak-mtld-pre	2026-10-17 15:33:12.991109508 +0800
+++ proposal_v14_zh.md	2026-10-17 15:34:00.403421061 +0800
@@ -298,23 +298,14 @@
 
 MTLD（采用 lexical_diversity 参考值，人类均值为 13.3，AI 均值介于 14.3-15.3）在整体分类器中仍是重要性最高的特征，占特征重要性的 34.0%，但其单变量区分能力有限，原因在于参考值在各条件间的方差很窄（约 0.4）。主导地位的排序得以保持，但绝对效应量应谨慎解读。这一发现值得注意，因为 H3（TTR）的原始组间差异仅在 9 个条件中的 5 个显著（长度控制后为 4/9、方向反转），而 MTLD 却是多变量框架中最有力的判别指标。这表明词汇多样性差异是细微的，分布在整个特征空间之中，而不是表现为较大的单变量效应。随机森林分类器能够捕捉单变量假设检验所遗漏的指标之间的非线性交互。
 
+
+MTLD 作为判别特征的地位，还有一层要问：其中有多少来自文本长度？把词数作为第 9 个特征加入后，准确率升至 95.7%，词数成为第二重要特征（28.1%），MTLD 从 34.0% 降到 29.4%，说明长度与 MTLD 共享大量方差；不使用 MTLD 的七特征分类器仍有 91.0% 的原始准确率，比多数类基线高约 1 个百分点。长度匹配子样本（400-800 词；12 篇人类、212 篇 AI）中 MTLD 仍居首位（34.8%），但准确率低于该子样本的多数类基线，结论无定论；条件层面的 MTLD 与长度相关只在 10 个条件中的 3 个显著，TTR 的长度依赖反而更强（平均 |r| 为 0.446）。保守的读法是：MTLD 的主导地位被长度部分解释、未被完全解释，需要在 N=90 上以残差化把两者分开。
 ### 词汇多样性：方向冲突与 MTLD 方差异常
 
 三个词汇多样性指标在组水平上的方向并不一致。TTR 表明 AI 文本的词汇多样性*更低*（TTR 更低；中位数 d = −0.42，在 5/9 中显著），而移动平均类符形符比（MATTR，窗口 100）与 MTLD 则表明 AI 文本*更多样*（中位数 d = +1.66 和 +2.03；在 9/9 中显著）。这正是本报告所述长度混淆的一个缩影：TTR 对长度高度依赖（全样本中 TTR 与词数之间的 r ≈ −0.54），而此处的 AI 文本比人类文本长约 1.6 倍，因此 TTR 出现方向反转在意料之中；MATTR 与 MTLD 与长度的关联弱得多（r 分别约为 +0.22 和 +0.12）。与此一致，长度控制大体消解了这一冲突：原始的「AI 的 TTR 更低」差异不再以该形式存在，残差化后幸存的差异（4/9）反转为 AI > 人类——与 MATTR 和 MTLD 对齐（§3.2）。我们明确报告这一冲突及其「由长度塑形」的消解；计划中的 N=90 复现应对其作出正式判定。
 
 第二个异常关乎 MTLD 的*方差*结构：它是唯一一个 AI 各组的模型内部方差超过人类组的指标（方差比中位数为 2.40；仅在 1/9 个模型中更小），同时却表现出最大的均值差异效应（中位数 d = +2.03）。没有其他指标出现这种均值与方差相分离的情况。可能的机制——MTLD 的分段阈值构造、残余的长度效应，或真实的跨模型变异——都留待 N=90 复现加以检验。据此，不应把 MTLD 视为本报告中最强的判别指标（另见下文关于分类器的提醒）。
 
-### MTLD 的主导地位与文本长度
-
-一个关键顾虑是：MTLD 的 34.0% 特征重要性反映的是真实的词汇多样性差异，还是仅仅与文本长度相关。在本数据集中，AI 生成文本一致地长于人类文本（表 1）：平均词数从 531（GPT-3.5）到 878（Muse-Spark），而人类文本为 439；且 AI 文本的条件内长度变化（SD 28-116 词）远小于人类文本（SD 245 词）。由于 MTLD（采用修正后的 lexical_diversity 取值，各条件间方差很小）比最初的定制实现更不易受文本长度混淆，因而更独立于词汇多样性。
-
-有三项证据回应这一顾虑。第一，条件之间的长度差异很大（人类 439 ± 245 词 vs AI 531-878 词；AI 的平均长度为人类均值的 1.4 倍）；分类器作用的是条件间方差，因此条件内相关并不是相关的辩护理由。我们加入词数作为第 9 个特征（见下文），以直接量化长度的增量贡献；10 个条件中只有 3 个显示出显著相关（Human r=+0.67，p<0.001；Claude r=+0.44，p=0.016；Muse-Spark r=+0.43，p=0.019）。值得注意的是，GPT-3.5 呈负相关且不显著（r=-0.14，p=0.47），表明长度并未在各条件间一致地驱动 MTLD。相比之下，TTR 表现出更强的长度依赖性（平均 |r|=0.446，在 10 个条件中的 6 个显著），证实了文本长度与类符形符比之间已知的数学关系。
-
-第二，一项长度匹配子样本分析（限定为 400–800 词的文本，保留 12/30 个人类样本和 212/269 个 AI 样本）给出两个关键结果：（a）随机森林分类器达到 94.2% ± 2.0% 的原始准确率——在该子样本（12 个人类 + 212 个 AI）中，这一数值低于 94.6% 的多数类基线（12/(12+212)）。94.2% 的原始准确率低于多数类基线，且 n=12 个人类样本不足以提供可靠估计平衡准确率所需的统计功效；该子样本分析对于「MTLD 的区分能力是否独立于文本长度」是无定论的。这一问题留待 N=90 的残差化分析（未来工作）。（b）MTLD 在该子样本中保持 34.8% 的特征重要性，但鉴于整体准确率无定论，这一发现只是提示性的，而非确凿的。
-
-第三，当把词数作为第 9 个特征加入分类器时，准确率升至 95.7%，词数本身成为仅次于 MTLD（29.4%）的第二重要特征（28.1%）；MTLD 从 34.0% 降至 29.4%（下降 4.6 个百分点），而词数吸收了 28.1% 的重要性，表明长度与 MTLD 之间存在大量共享方差。一个不加入 MTLD 训练的分类器（仅使用其余 7 个特征）仍达到 91.0% 的原始准确率（比 90.0% 的多数类基线高约 1 个百分点），表明其余特征可能独立承载了不可忽略的信号。此处不报告无 MTLD 消融（ablation）的平衡准确率，因为这需要在不含 MTLD 特征的情况下重新运行 StratifiedGroupKFold 流程；这一点留待补充材料。
-
-最保守的解释是：MTLD 的主导地位被长度部分解释，但未被完全解释。总特征重要性中约 28% 由词数捕获，不过它与 MTLD 共享大量方差（相关分析 §4）；区分能力的归因需要 N=90 的残差化分析。MTLD 的区分能力虽然在多变量分类器中仍然显著，但与文本长度部分混淆；基于残差化的裁定留待 N=90（未来工作）。借助修正后的 lexical_diversity 取值与长度控制分析，MTLD 方向与 TTR 方向之间的矛盾得以消解：长度控制后，TTR 的幸存差异反转为 AI > 人类，与 MATTR 和 MTLD 对齐（§3.2、§4）。N=90 的未来工作应通过基于回归的方法（例如对词数回归后取残差的残差化 MTLD）或精确的长度匹配设计来正式控制长度。
 
 ## 5. 结论
 

