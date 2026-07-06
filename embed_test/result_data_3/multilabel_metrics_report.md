# Embedding 모델 Multi-label 평가 리포트

> **출처**: `../multilabel_metrics_report.json` (자동 생성)  
> **재현**: `../multilabel_metrics_eval.py` / `../result_check3.ipynb`

- **데이터**: `result_data_3/result-{model}.csv` × `origin_data/movie_all_fixed.csv`
- **표본 수**: 11,384편
- **라벨 축**: genre (평균 2.1개/영화, 59라벨), theme (9.0개, 67라벨), mood (7.2개, 47라벨)
- **방법**: L2 정규화 임베딩, cosine kNN (`k=107`), 이웃 label 빈도 ≥ 0.5 → multi-label 예측
- **평가 모델**: bge-m3, qwen3-0.6B

---

## 1. Executive Summary


| 목적                      | 권장 모델          | 근거 (JSON)                                                              |
| ----------------------- | -------------- | ---------------------------------------------------------------------- |
| genre multi-label 검색/필터 | **Qwen3-0.6B** | samples F1 **0.603**, macro mAP **0.514**, separation margin **0.095** |
| theme 정밀도               | **Qwen3-0.6B** | samples F1 **0.488**, macro mAP **0.441**, separation margin **0.031** |
| mood 정밀도                | **Qwen3-0.6B** | samples F1 **0.637**, macro mAP **0.429**, separation margin **0.039** |
| 리소스·속도 우선               | **Qwen3-0.6B** | 3축 전부 1위, 1.5GB / 10 item/s                                            |
| bge-m3                  | baseline       | 3축 모두 열위 (genre samples F1 0.430)                                      |


**종합 순위 (samples F1 기준)**


| 라벨 축  | 1위                 | 2위             |
| ----- | ------------------ | -------------- |
| genre | qwen3-0.6B (0.603) | bge-m3 (0.430) |
| theme | qwen3-0.6B (0.488) | bge-m3 (0.359) |
| mood  | qwen3-0.6B (0.637) | bge-m3 (0.568) |


**label-wise Silhouette (support 가중 macro)** 는 2모델·3축 모두 **양수**(0.009 ~ 0.021). primary-label 단일 군집 Silhouette(별도 PaCMAP 분석, 음수 구간)와 달리 multi-label aware 지표가 ontology 구조를 더 잘 반영합니다.

---

## 2. 핵심 지표 (모델 × 라벨축)

### Genre


| model          | samples F1 | samples Jaccard | macro F1  | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| -------------- | ---------- | --------------- | --------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3         | 0.430      | 0.364           | 0.061     | 0.077          | 0.409     | 0.055       | 0.010           | 0.028     | 0.393     | 0.622          | 0.193       |
| **qwen3-0.6B** | **0.603**  | **0.521**       | **0.133** | **0.167**      | **0.514** | **0.095**   | **0.021**       | **0.022** | **0.541** | **0.446**      | **0.290**   |


**micro 지표 (genre)**


| model      | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ---------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3     | 0.751   | 0.310   | 0.439    | 0.281         | 0.097                 |
| qwen3-0.6B | 0.823   | 0.484   | 0.609    | 0.438         | 0.114                 |


### Theme


| model          | samples F1 | samples Jaccard | macro F1  | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| -------------- | ---------- | --------------- | --------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3         | 0.359      | 0.240           | 0.116     | 0.116          | 0.409     | 0.015       | 0.009           | 0.115     | 0.317     | 0.738          | 0.000       |
| **qwen3-0.6B** | **0.488**  | **0.345**       | **0.191** | **0.191**      | **0.441** | **0.031**   | **0.012**       | **0.105** | **0.400** | **0.609**      | **0.004**   |


**micro 지표 (theme)**


| model      | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ---------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3     | 0.731   | 0.237   | 0.357    | 0.218         | 0.144                 |
| qwen3-0.6B | 0.746   | 0.333   | 0.461    | 0.299         | 0.150                 |


### Mood


| model          | samples F1 | samples Jaccard | macro F1  | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| -------------- | ---------- | --------------- | --------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3         | 0.568      | 0.422           | 0.185     | 0.185          | 0.395     | 0.020       | 0.011           | 0.107     | 0.468     | 0.515          | 0.009       |
| **qwen3-0.6B** | **0.637**  | **0.491**       | **0.243** | **0.243**      | **0.429** | **0.039**   | **0.020**       | **0.099** | **0.525** | **0.418**      | **0.018**   |


**micro 지표 (mood)**


| model      | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ---------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3     | 0.743   | 0.464   | 0.571    | 0.400         | 0.184                 |
| qwen3-0.6B | 0.744   | 0.551   | 0.633    | 0.463         | 0.200                 |


---

## 3. Label-wise Highlights (JSON `labelwise_top5` / `labelwise_bottom5`)

### Genre — 라벨별 F1 상위 5


| 순위  | bge-m3     | qwen3-0.6B |
| --- | ---------- | ---------- |
| 1   | 드라마 0.736  | 액션 0.849   |
| 2   | 액션 0.703   | 드라마 0.779  |
| 3   | SF 0.498   | 어드벤처 0.737 |
| 4   | 어드벤처 0.404 | SF 0.699   |
| 5   | 공포 0.352   | 스릴러 0.693  |


### Theme — 라벨별 F1 상위 5


| 순위  | bge-m3               | qwen3-0.6B           |
| --- | -------------------- | -------------------- |
| 1   | uncertainty 0.738    | uncertainty 0.781    |
| 2   | self_discovery 0.700 | social_change 0.765  |
| 3   | betrayal 0.695       | betrayal 0.750       |
| 4   | social_change 0.638  | self_discovery 0.744 |
| 5   | isolation 0.522      | paranoia 0.623       |


### Mood — 라벨별 F1 상위 5


| 순위  | bge-m3            | qwen3-0.6B        |
| --- | ----------------- | ----------------- |
| 1   | intense 0.845     | intense 0.854     |
| 2   | suspenseful 0.815 | suspenseful 0.832 |
| 3   | melancholic 0.786 | melancholic 0.807 |
| 4   | surreal 0.748     | surreal 0.770     |
| 5   | wonder 0.707      | wonder 0.747      |


### 공통 저성능 라벨 (F1 = 0, 2모델 공통)


| 축     | 라벨            | 비고                                  |
| ----- | ------------- | ----------------------------------- |
| genre | 활극            | support 59                          |
| genre | 로드무비          | support 55 (qwen3-0.6B), bge-m3 미평가 |
| theme | humanity      | support 283                         |
| theme | acceptance    | support 336                         |
| mood  | gritty        | support 52                          |
| mood  | gentle        | support 302                         |
| mood  | futuristic    | support 629                         |
| mood  | introspective | support 504                         |


---

## 4. Separation Margin 상위 라벨 (JSON `separation_top5`)

centroid intra − inter cosine. 값이 클수록 해당 라벨이 임베딩 공간에서 더 잘 분리됨.

### Genre


| bge-m3      | qwen3-0.6B      |
| ----------- | --------------- |
| 반공/분단 0.123 | 반공/분단 **0.160** |
| 신파 0.114    | 신파 0.157        |
| 활극 0.112    | 스포츠 0.143       |
| 문예 0.102    | 종교 0.137        |
| 무협 0.093    | 활극 0.137        |


### Theme


| bge-m3                     | qwen3-0.6B                 |
| -------------------------- | -------------------------- |
| first_love 0.035           | first_love **0.054**       |
| memory 0.029               | love 0.052                 |
| emotional_connection 0.029 | emotional_connection 0.052 |
| magic 0.028                | conspiracy 0.051           |
| faith 0.027                | family 0.051               |


### Mood


| bge-m3          | qwen3-0.6B       |
| --------------- | ---------------- |
| angry 0.045     | epic **0.082**   |
| epic 0.044      | adrenaline 0.069 |
| gritty 0.043    | funny 0.064      |
| enigmatic 0.042 | joyful 0.061     |
| varied 0.038    | awe 0.060        |


---

## 5. result_data_2 (6,204편) 대비 변화


| 항목        | result_data_2                          | result_data_3                      |
| --------- | -------------------------------------- | ---------------------------------- |
| 표본 수      | 6,204                                  | **11,384**                         |
| ontology  | movie_ontology.csv                     | movie_all_fixed.csv                |
| result 라벨 | genres만 (themes/moods는 ontology merge) | genres, moods, themes, keywords 포함 |
| kNN k     | 79 (√6204)                             | **107** (√11384)                   |
| 평가 모델     | bge-m3, qwen3-0.6B, qwen3-4B-1024      | bge-m3, qwen3-0.6B                 |


**qwen3-0.6B genre samples F1**: 0.806 (6,204편) → **0.603** (11,384편). 데이터 확장·라벨 분포 변화로 절대값은 낮아졌으나, bge-m3 대비 상대 우위(genre +0.17)는 유지됩니다.

---

## 6. 해석 및 권장

### 관찰

1. **k=107 kNN** 기준 Qwen3-0.6B가 genre·theme·mood 전 축에서 bge-m3 대비 우위. genre 격차가 가장 큼 (0.603 vs 0.430).
2. **theme** 은 라벨 수(67)·영화당 평균 9.0개로 난이도가 높아 samples F1 전반적으로 낮음 (최고 0.488). subset accuracy ≈ 0.004 수준.
3. **macro label F1 ≪ samples F1** (genre qwen3-0.6B: 0.167 vs 0.603): 빈도 높은 라벨에서 samples F1이 높지만, macro는 희귀 라벨 F1=0에 크게 끌림.
4. **knn_label_jaccard_samples** (이웃 label union vs true set)는 samples Jaccard보다 낮음 → threshold 0.5 majority vote가 일부 라벨을 과예측/과소예측.
5. **separation margin** macro: genre에서 Qwen(0.095) ≫ bge-m3(0.055). theme/mood도 Qwen이 전 축에서 우위.

### 권장


| 시나리오                      | 선택                                                                      |
| ------------------------- | ----------------------------------------------------------------------- |
| genre/theme/mood 기반 필터·추천 | **Qwen3-0.6B**                                                          |
| VRAM·latency 제약           | **Qwen3-0.6B** (1.5GB / 10 item/s)                                      |
| baseline·비교 기준            | **bge-m3**                                                              |
| 품질 게이트 지표                 | samples F1/Jaccard, macro mAP, separation margin, label-wise silhouette |
| PaCMAP·primary Silhouette | 탐색용만 사용                                                                 |


### 후속 개선

- 희귀 라벨 (`humanity`, `introspective`, `gentle` 등) — support는 있으나 F1=0 → hierarchical label, re-sampling, contrastive fine-tuning
- theme subset accuracy 극저 → multi-label retrieval 평가체계를 exact-match 대신 **partial F1/Jaccard** 중심으로 운영
- **Qwen3-4B** 임베딩 추가 시 3모델 비교 리포트 갱신
- k·threshold 튜닝 (`k=107`, vote ≥ 0.5) — `coverage`·`ranking_loss` 교차 검증

---

## 7. 산출물


| 파일                                  | 내용                                                     |
| ----------------------------------- | ------------------------------------------------------ |
| `../multilabel_metrics_report.json` | 본 리포트 원본 (summary + labelwise top/bottom + separation) |
| `../multilabel_metrics_summary.csv` | summary 테이블 CSV                                        |
| `../multilabel_metrics_eval.py`     | 재현 스크립트 (`KNN_K=107`)                                  |
| `../result_check3.ipynb`            | PaCMAP 시각화 + multi-label 평가 셀                          |
| `result-{model}.csv`                | 모델별 임베딩 결과 (11,384편)                                   |


