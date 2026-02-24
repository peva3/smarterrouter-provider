# Benchmark Gap Analysis Report

## Executive Summary
Comprehensive search identified **263 benchmark datasets** on HuggingFace, with **248 not covered** by current 33 sources. Major gaps exist in multilingual, multimodal, safety, commonsense reasoning, and domain-specific benchmarks.

## Current Coverage (33 Sources)
- **ELO**: LMSYS Arena, Arena.ai
- **Reasoning**: LiveBench, GSM8K, ARC, BBH, AGIEval, MathVista, FrontierMath, AIME, StatEval, GPQA, MATH, HellaSwag
- **Coding**: BigCodeBench, HumanEval, SWE-bench, Aider, LiveCodeBench, SciCode, Tool Use
- **General**: MMLU, MMLU-Pro, MixEval-X, Chinese, AILuminate, MEGA-Bench, HELM, Domain-Specific, Vision, TruthfulQA, Safety, Multilingual

## Gap Analysis by Category

### 1. Multilingual Benchmarks (65 datasets)
**Current**: Chinese benchmarks only
**Missing**: C-Eval, C-MMLU, XGLUE, XTREME, multilingual variants of MMLU
**Priority**: High - RouterEngine supports multilingual routing

### 2. Multimodal/Vision Benchmarks (58 datasets)
**Current**: Vision.py, MathVista
**Missing**: VQAv2, GQA, CLEVR, VizWiz, TextVQA, DocVQA, ChartQA, ScienceQA
**Priority**: Medium - Vision capability detection via keywords

### 3. Math Benchmarks (40 datasets)
**Current**: GSM8K, MathVista, FrontierMath, AIME
**Missing**: Hendrycks MATH (standard benchmark), TheoremQA
**Priority**: High - MATH is standard for reasoning evaluation

### 4. Safety/Alignment Benchmarks (7 datasets)
**Current**: AILuminate
**Missing**: TruthfulQA, OpenAI moderation API evaluation, toxicity detection
**Priority**: Medium - Important for responsible AI routing

### 5. Commonsense Reasoning (6 datasets)
**Current**: None
**Missing**: HellaSwag, WinoGrande, PIQA, SocialIQA
**Priority**: Medium - Important for general reasoning

### 6. Question Answering (34 datasets)
**Current**: None specific
**Missing**: SQuAD, RACE, DROP, Natural Questions, HotpotQA
**Priority**: Low - Covered by general knowledge benchmarks

### 7. Domain-Specific (19 datasets)
**Current**: Domain-specific.py (generic)
**Missing**: Medical (Health Benchmarks), Legal, Financial, Scientific
**Priority**: Medium - Important for specialized use cases

## Most Promising New Source
**Dataset**: `nlile/math_benchmark_test_saturation`
- **Type**: Math reasoning benchmark (Hendrycks MATH)
- **Models**: 112 unique models with accuracy scores
- **Mappability**: 52.7% to known model families
- **Data**: Contains model names, accuracy (0-100), year, parameters
- **Use**: Could enhance reasoning_score for MATH benchmark

## Other High-Value Targets
1. **TruthfulQA** - Factual accuracy/general knowledge
2. **HellaSwag** - Commonsense reasoning/general  
3. **C-Eval/C-MMLU** - Chinese/multilingual general knowledge
4. **OpenAI Moderation API Evaluation** - Safety/alignment
5. **VQAv2/GQA** - Vision-language multimodal

## Implementation Recommendations

### Phase 1 (Immediate)
1. **Add Hendrycks MATH benchmark fetcher**
   - Source: `nlile/math_benchmark_test_saturation` HuggingFace dataset
   - Category: Reasoning
   - Mapping: Use existing model_mapper patterns

2. **Add TruthfulQA fetcher**
   - Source: HuggingFace or PapersWithCode
   - Category: General (factual accuracy)
   - Priority: High for truthfulness evaluation

### Phase 2 (Near-term)
3. **Add HellaSwag fetcher** - Commonsense reasoning
4. **Add C-Eval/C-MMLU fetcher** - Multilingual general knowledge  
5. **Add multilingual benchmark aggregator**

### Phase 3 (Future)
6. **Add safety benchmark suite** (TruthfulQA, moderation API, toxicity)
7. **Add multimodal benchmark aggregator**
8. **Add domain-specific benchmark suite**

## Technical Considerations
- **Mapping**: New sources need model name → OpenRouter ID mapping
- **Normalization**: Scores must be converted to 0-100 scale
- **Conflict resolution**: Multiple sources per category need weighting
- **RouterEngine compatibility**: Must match schema (reasoning_score, coding_score, general_score, elo_rating)

## Expected Impact
Adding 5-10 high-quality benchmark sources could:
- Increase model coverage by 15-30%
- Improve score accuracy through multi-source consensus
- Enable better routing for specialized tasks (multilingual, multimodal, domain-specific)
- Maintain SmarterRouter compatibility while enhancing robustness

## Files Generated
1. `research/benchmark_datasets_v2.json` - 263 filtered benchmark datasets
2. `research/missing_benchmarks.json` - 248 missing benchmarks  
3. `research/promising_benchmarks.json` - 1 promising dataset with evaluation scores
4. `research/benchmark_gap_analysis.md` - This report

## Next Steps
1. Implement Hendrycks MATH benchmark fetcher
2. Test integration with builder.py
3. Validate RouterEngine compatibility
4. Run full build and compare coverage metrics
5. Iterate with additional high-priority benchmarks