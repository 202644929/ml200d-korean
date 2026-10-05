# Magic Lantern 200D 한국어 패치

Canon EOS 200D(Kiss X9, 펌웨어 1.0.1)용 [Magic Lantern](https://github.com/reticulatedpines/magiclantern_simplified) 메뉴를 한국어로 바꾸는 패치입니다.

한국어 패치는 Claude(LLM)가 작성했고, 개인 빌드 전용입니다. 작업은 PC 두 대에서 이어서 했습니다.

ML에는 원래 다국어(i18n) 기능이 없습니다. 메뉴 문장이 C 코드에 직접 적혀 있어서, 번역 기능을 처음부터 새로 만들었습니다.

## 1단계: 첫 번째 PC (~2026-09-14)

새로 만든 파일 (원본 저장소에 없음)

- `tools/i18n/extract_strings.py`: 소스 코드에서 메뉴 문장을 뽑아내고, 파일·줄·항목 기준으로 번호를 붙입니다.
- `tools/i18n/strings_ko.csv`: 뽑아낸 영어 문장과 한국어 번역을 나란히 적은 표입니다.
- `tools/i18n/gen_ko_overrides.py`: 이 표를 C 코드로 바꿔 줍니다.
- `src/ko_overrides.c`: 그렇게 만들어진 번역표입니다.

고친 기존 파일

- `src/menu.c`: 메뉴를 그릴 때 번역표를 확인합니다. 번역이 있으면 한국어를, 없으면 영어 원문을 보여 줍니다. 한국어 문장에는 이름 줄이기(junkie_get_shortname)를 쓰지 않습니다. 글자가 중간에서 잘리기 때문입니다.
- `src/rbf_font.c`: "1바이트 = 1글자"로 계산하던 것을 UTF-8 글자 단위로 읽게 바꿨습니다. 한글은 한 글자가 3바이트입니다. 영문은 예전과 똑같이 동작합니다.
- `platform/Makefile`: 빌드할 때 `ko_overrides.c`가 같이 들어가도록 했습니다.

### 멈춘 지점

실기 200D에 설치하니 메뉴 글자가 하나도 보이지 않았습니다. 기존 `.rbf` 폰트에는 영문(32~159번 글자)만 있습니다. 그래서 한글은 글자 폭이 0으로 계산되어 아무것도 그려지지 않았습니다. 번역문은 펌웨어에 들어갔지만, 그 글자를 그릴 모양이 없었던 것입니다. 이 상태로 인수인계해서 다른 PC로 넘겼습니다.

## 2단계: 두 번째 PC (2026-09-15)

새로 만든 파일

- `tools/i18n/gen_kox.py`: 번역에 쓰인 한글 글자를 모아 `.kox` 폰트를 만듭니다. 카메라가 그리는 방식 그대로 검증 이미지도 뽑아 줍니다.
- `ML/fonts/*.kox`: 새로 만든 한글 폰트 형식입니다.
  - 기존 `.rbf` 크기마다 하나씩, 모두 6개입니다.
  - 번역에 쓰인 완성형 음절 588자가 들어 있고, 부팅할 때 불러옵니다.
  - 메뉴는 Noto Sans KR, 작은 글씨는 Galmuri11을 썼습니다. 둘 다 OFL 라이선스입니다.

고친 기존 파일

- `src/rbf_font.c`, `src/rbf_font.h`: 기존 폰트에 없는 글자는 `.kox`에서 모양과 폭을 가져옵니다. 1단계 패치 때문에 탭과 캐논 대체 폰트 폭이 0으로 나오던 문제도 같이 고쳤습니다.
- `src/ko_overrides.c`, `gen_ko_overrides.py`: 카드에 `.kox`가 없으면 영어 원문을 보여 줍니다. 빈 화면이 다시 나오지 않게 하려는 것입니다.
- `platform/Makefile`: 빌드할 때 `.kox`를 카드용 폴더에 복사합니다.
- `platform/200D.101/modules.included`: dot_tune 모듈을 뺐습니다. 200D에는 AF 미세조정(AFMA)이 없습니다. 넣어 두면 모듈 하나가 실패하면서 다른 모듈까지 전부 안 켜집니다.
- `src/menu.c`, `src/zebra.c`: 벤치마크 결과를 화면에 띄우고 스크린샷으로 저장합니다.

원본의 영어 메뉴 문장과 기존 `.rbf` 폰트 파일은 하나도 고치지 않았습니다. 새 버전이 나와도 번역표만 다시 맞추면 됩니다.

## 3단계: 언어 공통 구조로 바꿈 (2026-10-05)

한국어에만 맞춰져 있던 구조를 다른 언어도 같은 방식으로 넣을 수 있게 바꿨습니다. 한국어 결과물은 그대로입니다. 빌드한 `autoexec.bin` 크기와 번역표가 바꾸기 전과 똑같습니다. **이 단계는 아직 실기 200D에서 확인하지 않았습니다.**

이름과 위치가 바뀐 것

- `ko_tr()` → `i18n_tr()`
- `src/ko_overrides.c` → 빌드할 때 `build/i18n_strings.c`로 자동 생성되고, 소스에는 없습니다.
- `tools/i18n/strings_ko.csv` → `tools/i18n/lang/ko.csv` (번역 열 이름 `korean` → `translation`)
- `.kox` → `.rbx` (`RBF 확장`의 줄임말)
  - 파일 머리는 `RBX1`이고, 내용은 그대로입니다.
  - 카드 경로는 `ML/FONTS/*.RBX`입니다.
  - 폰트 파일은 `data/fonts/ko/`에 있습니다.
- `gen_ko_overrides.py` → `gen_strings.py`
- `gen_kox.py` → `gen_rbx.py`

새로 생긴 것

- `make ML_LANG=ko`: 빌드할 때 언어를 고릅니다.
  - 지정하지 않으면 영어이고, 번역이 들어가지 않습니다.
  - 변수 이름이 `LANG`이 아닌 이유: `LANG`은 셸의 로캘 변수와 겹칩니다.
- `gen_rbx.py`
  - 언어별 폰트는 파일 맨 위의 `LANG_FONTS` 표에서 정합니다.
  - 번역에 쓴 글자가 폰트에 없으면 실패하고, 어떤 글자인지 알려 줍니다.
- `extract_strings.py` → `template.csv`: 소스에서 문장을 새로 뽑습니다.
- `merge_lang.py --lang <코드>`: 뽑은 문장을 언어 CSV에 합칩니다.
  - 줄 번호가 밀려도 기존 번역을 지우지 않습니다.
  - 사라진 번역이 있으면 경고를 냅니다.
- `tools/i18n/tests/`: 테스트 22개
- `tools/i18n/README.md`: 번역자용 안내

알려진 한계

- 번역이 기존 폰트 안의 글자(라틴 문자)만 쓰는 언어(독일어·프랑스어 등)는 아직 안 됩니다.
- 언어를 바꿔 빌드할 때는 먼저 `make clean`을 해야 합니다.

## 그 밖에 200D용으로 바꾼 것

- `platform/200D.101/features.h`: 꺼져 있던 기능을 켰습니다. 하나씩 켜고 빌드해서 확인했습니다.
- `platform/200D.101/consts.h`: 트랩 포커스에 필요한 화면 위치 값이 200D에만 빠져 있어서 추가했습니다. 값은 100D/650D/700D와 같습니다.
- `src/shoot.c`, `src/focus.c`: 기본값을 바꿨습니다. 고급 브라케팅은 3장·2EV, 포커스 스태킹은 앞뒤 1장씩입니다.

## 결과

- 200D 실기에서 한국어 메뉴가 정상적으로 표시됩니다(2026-09-15 확인).
- 2026-10-05에 두 PC 작업을 하나로 합쳤고, 빌드를 다시 확인했습니다.

## 이 저장소에 있는 것

- `ml200d-ko.patch`: 위 변경 전체입니다(3단계 포함). 원본 `magiclantern_simplified`의 `dev` 브랜치 커밋 `BASE_COMMIT`에 적용합니다.
- `tools/i18n/`: 번역표(`lang/ko.csv`), 스크립트, 테스트, 안내서입니다.
- `data/fonts/ko/*.rbx`: 한글 글자 모양 파일입니다.
- 카드에 바로 넣을 빌드: [Releases](../../releases)의 `magiclantern-200D-ko.zip`
  - 2단계(2026-09-15) 빌드라서 글자 파일이 아직 `.kox`입니다.
  - 3단계 빌드는 실기 확인 뒤에 올립니다.

## 직접 빌드하기

```sh
git clone https://github.com/reticulatedpines/magiclantern_simplified
cd magiclantern_simplified
git checkout $(cat ../ml200d-korean/BASE_COMMIT)
git apply ../ml200d-korean/ml200d-ko.patch
cd platform/200D.101
make clean
make ARM_BINPATH=/path/to/arm-none-eabi-12.3/bin ML_LANG=ko
# 결과: build/magiclantern.zip
```

- 빌드에는 `python3`가 필요합니다.
- 글자 파일을 다시 만들려면(`gen_rbx.py`) `python3-pil`, `python3-fonttools`, `fonts-noto-cjk`가 필요합니다.
- 작은 글씨용 [Galmuri11](https://github.com/quiple/galmuri)(OFL)을 `200d-ko/fonts/Galmuri11.ttf`에 두세요.

ARM GNU Toolchain 12.3을 쓰세요. 너무 새 gcc(15 등)로는 ML의 옛 Lua 소스가 빌드되지 않습니다.

## 카드에 설치할 때 주의할 점

- 이미 ML이 설치된 카드라면 zip 안의 파일을 카드에 덮어쓰면 됩니다. 처음 설치하는 방법은 Magic Lantern 공식 안내를 따르세요.
- `autoexec.bin`과 `ML/modules/200D_101.sym`은 항상 같이 바꾸세요. 하나만 바꾸면 모듈이 멈춥니다.
- 카드에 예전 `DOT_TUNE.MO`가 남아 있으면 지우세요.
- 3단계 빌드부터는 `ML/FONTS/*.RBX`를 읽습니다. 예전 `*.KOX`는 지워도 됩니다. 글자 파일이 없으면 메뉴는 영어로 나옵니다.
- 카메라가 비정상 종료된 뒤에는 `ML/modules/LOADING.LCK` 때문에 모듈이 안 켜질 수 있습니다. 지우세요.
- 펌웨어를 고치는 일이므로 문제가 생겨도 책임지지 않습니다.

## 라이선스

- 패치와 스크립트: GPL v2 (Magic Lantern과 같음, `LICENSE` 참고)
- `.kox` 폰트: Noto Sans KR, Galmuri11을 바탕으로 만들었습니다(SIL Open Font License 1.1).
