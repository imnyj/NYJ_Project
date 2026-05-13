# User Directives


## [2026-04-30 14:02]
papers/paper1에 기존에 했던 논문 작업을 옮겼어. CIoV에서 V2I Precaching을 위한 dwell time 예측 CVAE 모델 설계를 주제로 하고 있는데, 기존 내 논문에서 발전시키기 위해 feature에 리를 하여 디자인해봤어. 일단, 내용을 이해하고 요약정리하여 나에게 설명해볼래?

## [2026-04-30 14:08]
첨부된 파일들을 읽고 필요한 것들을 추리고 필요없는 것들을 삭제하자. 만약 따로 정리하여 간추릴있는 것들은 한 곳에 정리하도록 하자현재 초안 작성되어있을테고, 어딘가에 tex파일이 있다면 말이지. dataset 수집을 기다리는 중이야. local 학습이 목표다 보니 RSU 하나가 최대한 20만개 근처의 data를 쌓을 때까지 기다리고 있어.


## [2026-04-30 14:08] 논문 수정 + 시뮬레이션 수정 요청 사항 (원본: `사용자 요청 사항.md`)

* 논문 수정 요청
1. 요약이 너무 길으니 현재의 60% 수준으로 줄일 것.
2. 요즘 서론의 트렌드에 따라 서론을 더 탄탄한 구조로 재작성할 것.
3. \---의 표현은 AI가 자주 활용하는 표현이니 지양할 것.
4. ( )는 축약어와 수식에서만 사용할 것. 수식은 Equation (n)의 형식으로 사용.
5. reference를 더 추가할 필요가 있음.

   * CIoV (Content-Centric Internet of Vehicle) : IoT J.에 제출할 것이기 때문에, IoV에 더 초점이 간 느낌의 용어 사용 전략
   * V2I Precaching
   * V2V Precaching
   * Popularity-based precaching (요청될 content 혹은 요청될 시간 등을 예측)
   * Mobility prediction-based precaching (요청된 content를 어디에 얼마나 놓을지 예측)
   * Hybrid precaching (이동성과 popularity 등을 포함한 context를 기반으로 어디에 어떤 content를 둘 지 예측)
   * ML precaching (예측을 함에 있어서 ML 사용) \& DL precaching (예측을 함에 있어서 DL 사용)
   * snapshot 기반이나 RSU-Local 기반의 논문이 있다면 추가. (단, 어떤 점이 부족했는지 설명할 필요있음.)
   * Baselines의 각각 reference 필요. (해당 방안의 논문과 git 링크)
6. reference table 수정 필요.

   * 위에서 제안 방안과 비교가 필요한 항목을 업데이트.
   * Work를 Paper로 바꾸고 저자 정보는 빼고 \\cite{}만으로 표현.
   * D1\~D6를 언급했으니 Related works Section에서 해당 구분자에 대한 설명할 것.
   * Detail 항목을 추가하여 1\~3문장의 짧은 글로 각 방안 요약 설명.
7. cite와 reference가 맞는지 확인하여 수정할 것.



* 시뮬 수정 요청
1. 업데이트된 reference 중에서 비교가 필요한 방안들을 baselines로 추가.
2. baselines는 시뮬레이션 dataset이 나오기 전에 바로 제작 착수할 것.



## [2026-04-30 14:12]
이 세션에서는 paper1폴더를 활용하여 작업하도록 해. 다른 세션에서 paper2, paper2도 작업 중이니깐 말이야.

## [2026-04-30 14:15]
paper1에 필요한 작업을 모두 진행하도록 해.(뽑고 있는 dataset이 완성되기 전까지 진행 가능한 사항에 대하여)

## [2026-05-06 16:01]
제안 방안의 학습을 위해서 RSU 로컬 데이터는 20만 개 정도가 필요한게 맞아? 컴퓨터 3군데에서 뽑는데 2~3주 되었나? 이제 2만개가 되어가고 있어.

## [2026-05-06 16:16]
snapshot 기록 주기, libsumo step 간격, I/O 빈도 등의 점검을 해보고, RSU 로컬 데이터 요구량은 5만으로 생각하고 있을게
