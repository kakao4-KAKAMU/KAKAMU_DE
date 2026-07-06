# Embedding 모델 Multi-label 평가 리포트

> **출처**: `multilabel_metrics_report.json` (자동 생성)  
> **재현**: `multilabel_metrics_eval.py` / `result_check2.ipynb`

- **데이터**: `result_data_2/result-{model}.csv` × `origin_data/movie_ontology.csv`
- **표본 수**: 6,204편 (ontology 8,300편 중 매칭)
- **라벨 축**: genre (평균 2.1개/영화, 49라벨), theme (8.2개, 67라벨), mood (6.7개, 47라벨)
- **방법**: L2 정규화 임베딩, cosine kNN (`k=79`), 이웃 label 빈도 ≥ 0.5 → multi-label 예측
- **평가 모델**: bge-m3, qwen3-0.6B, qwen3-4B-1024

---

## 1. Executive Summary


| 목적                      | 권장 모델             | 근거 (JSON)                                                              |
| ----------------------- | ----------------- | ---------------------------------------------------------------------- |
| genre multi-label 검색/필터 | **Qwen3-0.6B**    | samples F1 **0.806**, macro mAP **0.791**, separation margin 0.185     |
| theme 정밀도               | **Qwen3-4B-1024** | samples F1 **0.432**, macro mAP **0.352**, separation margin **0.043** |
| mood 정밀도                | **Qwen3-4B-1024** | samples F1 **0.610**, macro mAP **0.382**, separation margin **0.055** |
| 리소스·속도 우선               | **Qwen3-0.6B**    | genre 1위 + 1.5GB / 10 item/s (4B 대비 4× 빠름)                             |
| bge-m3                  | baseline          | 3축 모두 최하위 (genre samples F1 0.489)                                     |


**종합 순위 (samples F1 기준)**


| 라벨 축  | 1위                    | 2위                    | 3위             |
| ----- | --------------------- | --------------------- | -------------- |
| genre | qwen3-0.6B (0.806)    | qwen3-4b-1024 (0.763) | bge-m3 (0.489) |
| theme | qwen3-4b-1024 (0.432) | qwen3-0.6b (0.386)    | bge-m3 (0.263) |
| mood  | qwen3-4b-1024 (0.610) | qwen3-0.6b (0.588)    | bge-m3 (0.506) |


**label-wise Silhouette (support 가중 macro)** 는 3모델·3축 모두 **양수**(0.010 ~ 0.051). primary-label 단일 군집 Silhouette(별도 분석, −0.06 ~ −0.16)와 달리 multi-label aware 지표가 ontology 구조를 더 잘 반영합니다.

---



## 2. 핵심 지표 (모델 × 라벨축)



### Genre


| model          | samples F1 | samples Jaccard | macro F1 | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| -------------- | ---------- | --------------- | -------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3         | 0.489      | 0.422           | 0.097    | 0.119          | 0.409     | 0.041       | 0.012           | 0.031     | 0.451     | 0.560          | 0.245       |
| **qwen3-0.6B** | **0.806**  | **0.740**       | 0.318    | **0.390**      | **0.791** | **0.185**   | **0.051**       | **0.015** | **0.755** | **0.241**      | **0.524**   |
| qwen3-4b-1024  | 0.763      | 0.693           | 0.295    | 0.361          | 0.743     | 0.185       | 0.038           | 0.018     | 0.707     | 0.266          | 0.472       |


**micro 지표 (genre)**


| model         | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ------------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3        | 0.792   | 0.356   | 0.491    | 0.326         | 0.114                 |
| qwen3-0.6B    | 0.948   | 0.683   | 0.794    | 0.659         | 0.197                 |
| qwen3-4b-1024 | 0.883   | 0.660   | 0.755    | 0.607         | 0.176                 |




### Theme


| model             | samples F1 | samples Jaccard | macro F1  | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| ----------------- | ---------- | --------------- | --------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3            | 0.263      | 0.170           | 0.082     | 0.082          | 0.318     | 0.008       | 0.010           | 0.110     | 0.263     | 0.815          | 0.002       |
| qwen3-0.6B        | 0.386      | 0.262           | 0.148     | 0.148          | 0.327     | 0.037       | 0.015           | 0.106     | 0.323     | 0.697          | 0.004       |
| **qwen3-4b-1024** | **0.432**  | **0.298**       | **0.173** | **0.173**      | **0.352** | **0.043**   | 0.013           | **0.103** | **0.348** | **0.648**      | **0.004**   |


**micro 지표 (theme)**


| model         | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ------------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3        | 0.734   | 0.154   | 0.254    | 0.146         | 0.140                 |
| qwen3-0.6B    | 0.672   | 0.256   | 0.370    | 0.227         | 0.143                 |
| qwen3-4b-1024 | 0.668   | 0.300   | 0.414    | 0.261         | 0.141                 |




### Mood


| model             | samples F1 | samples Jaccard | macro F1  | macro label F1 | macro mAP | sep. margin | label-wise sil. | hamming ↓ | LRAP      | ranking loss ↓ | subset acc. |
| ----------------- | ---------- | --------------- | --------- | -------------- | --------- | ----------- | --------------- | --------- | --------- | -------------- | ----------- |
| bge-m3            | 0.506      | 0.367           | 0.156     | 0.156          | 0.343     | 0.011       | 0.013           | 0.107     | 0.427     | 0.582          | 0.009       |
| qwen3-0.6B        | 0.588      | 0.443           | 0.221     | 0.221          | 0.363     | 0.053       | **0.025**       | 0.100     | 0.482     | 0.470          | 0.013       |
| **qwen3-4b-1024** | **0.610**  | **0.466**       | **0.235** | **0.235**      | **0.382** | **0.055**   | 0.024           | **0.099** | **0.499** | **0.431**      | **0.015**   |


**micro 지표 (mood)**


| model         | micro P | micro R | micro F1 | micro Jaccard | knn Jaccard (samples) |
| ------------- | ------- | ------- | -------- | ------------- | --------------------- |
| bge-m3        | 0.738   | 0.387   | 0.508    | 0.341         | 0.190                 |
| qwen3-0.6B    | 0.715   | 0.496   | 0.586    | 0.414         | 0.204                 |
| qwen3-4b-1024 | 0.703   | 0.538   | 0.610    | 0.438         | 0.201                 |


---



## 3. Label-wise Highlights (JSON `labelwise_top5` / `labelwise_bottom5`)



### Genre — 라벨별 F1 상위 5


| 순위  | bge-m3     | qwen3-0.6B | qwen3-4b-1024 |
| --- | ---------- | ---------- | ------------- |
| 1   | 액션 0.750   | 공포 0.914   | 공포 0.862      |
| 2   | 드라마 0.729  | 액션 0.911   | 액션 0.827      |
| 3   | 스릴러 0.580  | 코메디 0.911  | 어드벤처 0.818    |
| 4   | 공포 0.570   | 어드벤처 0.874 | 무협 0.817      |
| 5   | 어드벤처 0.554 | SF 0.861   | 드라마 0.815     |




### Theme — 라벨별 F1 상위 5


| 순위  | bge-m3               | qwen3-0.6B           | qwen3-4b-1024        |
| --- | -------------------- | -------------------- | -------------------- |
| 1   | uncertainty 0.664    | uncertainty 0.680    | uncertainty 0.716    |
| 2   | self_discovery 0.608 | self_discovery 0.658 | self_discovery 0.681 |
| 3   | betrayal 0.582       | betrayal 0.632       | betrayal 0.669       |
| 4   | hero_journey 0.417   | hero_journey 0.569   | social_change 0.603  |
| 5   | paranoia 0.396       | social_change 0.552  | hero_journey 0.593   |




### Mood — 라벨별 F1 상위 5


| 순위  | bge-m3            | qwen3-0.6B        | qwen3-4b-1024     |
| --- | ----------------- | ----------------- | ----------------- |
| 1   | intense 0.820     | intense 0.819     | intense 0.824     |
| 2   | suspenseful 0.800 | suspenseful 0.806 | suspenseful 0.812 |
| 3   | melancholic 0.731 | melancholic 0.770 | melancholic 0.774 |
| 4   | wonder 0.642      | wonder 0.724      | wonder 0.737      |
| 5   | surreal 0.610     | surreal 0.700     | surreal 0.709     |




### 공통 저성능 라벨 (F1 = 0, 3모델 공통 또는 다수)


| 축     | 라벨                                       | 비고                         |
| ----- | ---------------------------------------- | -------------------------- |
| genre | 로드무비, 하이틴(고교), 사회물(경향)                   | support ≤ 25               |
| genre | 멜로드라마                                    | support 187이나 F1 0 (3모델)   |
| theme | humanity                                 | support 141, F1 0 (3모델)    |
| mood  | introspective, found_footage, futuristic | support 53~346, F1 0 (3모델) |


---



## 4. Separation Margin 상위 라벨 (JSON `separation_top5`)

centroid intra − inter cosine. 값이 클수록 해당 라벨이 임베딩 공간에서 더 잘 분리됨.

### Genre


| bge-m3     | qwen3-0.6B      | qwen3-4b-1024 |
| ---------- | --------------- | ------------- |
| 무협 0.084   | 자연ㆍ환경 **0.292** | 서부 0.289      |
| 스포츠 0.068  | 인권 0.287        | 무협 0.263      |
| 옴니버스 0.066 | 종교 0.257        | 인권 0.258      |
| 서부 0.064   | 아동 0.255        | 자연ㆍ환경 0.257   |
| 종교 0.061   | 역사 0.239        | 종교 0.254      |




### Theme


| bge-m3                     | qwen3-0.6B                 | qwen3-4b-1024              |
| -------------------------- | -------------------------- | -------------------------- |
| first_love 0.028           | family 0.097               | love **0.103**             |
| love 0.025                 | love 0.093                 | first_love 0.094           |
| family 0.024               | acceptance 0.080           | family 0.089               |
| emotional_connection 0.023 | emotional_connection 0.078 | emotional_connection 0.084 |
| survival 0.021             | first_love 0.077           | friendship 0.082           |




### Mood


| bge-m3               | qwen3-0.6B         | qwen3-4b-1024      |
| -------------------- | ------------------ | ------------------ |
| epic 0.041           | epic **0.140**     | epic 0.130         |
| adrenaline 0.030     | adrenaline 0.123   | adrenaline 0.116   |
| claustrophobic 0.025 | funny 0.122        | funny 0.110        |
| gentle 0.024         | violent 0.099      | violent 0.090      |
| violent 0.022        | lighthearted 0.093 | lighthearted 0.090 |


---



## 5. 해석 및 권장



### 관찰

1. **k=79 kNN** 기준에서도 Qwen 계열이 bge-m3 대비 genre·theme·mood 전 축에서 우위. genre 격차가 가장 큼 (0.806 vs 0.489).
2. **theme** 은 라벨 수(67)·영화당 평균 8.2개로 난이도가 높아 samples F1 전반적으로 낮음 (최고 0.432). subset accuracy ≈ 0.004 수준.
3. **macro label F1 ≪ samples F1** (genre qwen3-0.6B: 0.390 vs 0.806): 빈도 높은 라벨에서 samples F1이 높지만, macro는 희귀 라벨 F1=0에 크게 끌림.
4. **knn_label_jaccard_samples** (이웃 label union vs true set)는 samples Jaccard보다 낮음 → threshold 0.5 majority vote가 일부 라벨을 과예측/과소예측.
5. **separation margin** macro: genre에서 Qwen(0.185) ≫ bge-m3(0.041). theme/mood도 Qwen 4B가 최고.



### 권장


| 시나리오                      | 선택                                                                      |
| ------------------------- | ----------------------------------------------------------------------- |
| genre 기반 필터·추천            | **Qwen3-0.6B**                                                          |
| theme/mood ontology 정렬    | **Qwen3-4B-1024**                                                       |
| VRAM·latency 제약           | **Qwen3-0.6B** (genre 1위, mood 2위)                                      |
| 품질 게이트 지표                 | samples F1/Jaccard, macro mAP, separation margin, label-wise silhouette |
| PaCMAP·primary Silhouette | 탐색용만 사용                                                                 |




### 후속 개선

- 희귀 라벨 (`멜로드라마`, `humanity`, `introspective` 등) — support는 있으나 F1=0 → hierarchical label, re-sampling, contrastive fine-tuning
- theme subset accuracy 극저 → multi-label retrieval 평가체계를 exact-match 대신 **partial F1/Jaccard** 중심으로 운영
- k·threshold 튜닝 (`k=79`, vote ≥ 0.5) — `coverage`·`ranking_loss` 교차 검증

---



## 6. 산출물


| 파일                               | 내용                                                     |
| -------------------------------- | ------------------------------------------------------ |
| `multilabel_metrics_report.json` | 본 리포트 원본 (summary + labelwise top/bottom + separation) |
| `multilabel_metrics_summary.csv` | summary 테이블 CSV                                        |
| `multilabel_metrics_eval.py`     | 재현 스크립트 (`KNN_K=79`)                                   |
| `result_check2.ipynb`            | PaCMAP 시각화 + multi-label 평가 셀                          |


