# 번역 도구 안내 (tools/i18n)

Magic Lantern(캐논 200D) 메뉴를 다른 언어로 바꾸는 도구 모음입니다.
별도 표시가 없는 명령은 WSL(또는 리눅스)에서 `tools/i18n` 폴더 안에서 실행합니다(빌드 단계만 저장소 맨 위에서 시작합니다).

## 무엇인가

- `lang/<언어코드>.csv` : 번역 표. 번역자가 고치는 파일은 이것 하나입니다. 언어 코드는 소문자 두 글자입니다(`ko`, `ja`, `de` …).
- `template.csv` : 소스에서 뽑은 영어 문장 목록. 직접 고치지 않습니다(자동 생성).
- 표의 열: `id, file, line, field, english, translation, status, note`
  - `english` : 영어 원문. **번역 찾기의 열쇠이므로 절대 고치지 마세요.** 고치면 그 번역은 다음 합치기 때 사라집니다.
  - `translation` : 번역문. 여기만 채웁니다. 비워 두면 영어가 그대로 나옵니다.
  - `status` : `new`(아직 번역 안 함) 또는 `translated`(번역함). 번역을 채웠으면 `translated`로 바꿉니다.
  - `note` : 메모용. 비워 둬도 됩니다.
- 영어(`en`)는 번역 파일이 필요 없습니다. 기본 빌드가 영어입니다.

## 새 언어 추가

예: 일본어(`ja`).

```
cd tools/i18n
python3 extract_strings.py
python3 merge_lang.py --lang ja
```

`lang/ja.csv`가 생기고 모든 줄이 `status=new`, `translation` 빈칸으로 시작합니다.
`translation`을 채우고 `status`를 `translated`로 바꾸세요. 그다음 아래 "폰트"와 "빌드"로 넘어갑니다.

## 번역 고치기

1. `lang/<코드>.csv`를 엽니다. 엑셀로 열면 글자가 깨질 수 있으니 UTF-8을 지원하는 편집기를 쓰세요. 쉼표나 따옴표가 든 칸은 큰따옴표로 감싼 형태를 유지합니다.
2. `translation`만 고칩니다. `id`, `english` 등 다른 열은 건드리지 않습니다.
3. **`python3 gen_rbx.py --lang <코드>`를 다시 돌립니다.** 번역에 지금 폰트에 없는 새 글자를 썼다면 `data/fonts/<코드>/*.rbx`를 갱신해야 합니다. 안 하면 카메라에서 그 글자가 빈칸으로 나옵니다. 간단한 규칙: 번역을 고칠 때마다 `gen_rbx.py`를 다시 돌리세요(결과가 같으면 파일은 그대로입니다).
4. 저장 후 다시 빌드합니다(아래 "빌드").

## 원본 소스가 바뀌었을 때

ML 소스에 메뉴 문장이 추가·수정·삭제되면 번역 표를 맞춥니다.

```
cd tools/i18n
python3 extract_strings.py
python3 merge_lang.py --lang ko
```

- 영어 문장이 같으면 기존 번역을 그대로 가져옵니다(줄 번호가 바뀌어도 괜찮습니다).
- 새 문장은 `status=new`, `translation` 빈칸으로 들어옵니다. `status`가 `new`인 줄을 찾아 번역하면 됩니다.
- 영어 문장이 바뀌어 번역을 가져오지 못하면 화면(stderr)에 `lost`로 알려 줍니다. 목록을 보고 새 줄에 다시 반영하세요.
- 언어가 여러 개면 언어마다 `merge_lang.py --lang <코드>`를 한 번씩 실행합니다.
- 새로 번역한 문장에 지금 폰트에 없는 글자가 있으면 `python3 gen_rbx.py --lang <코드>`를 다시 돌려 `data/fonts/<코드>/*.rbx`를 갱신하세요. 안 하면 카메라에서 그 글자가 빈칸으로 나옵니다.

## 폰트

번역에 쓴 글자 모양은 `.rbx` 파일로 만들어 카드에 넣습니다. 글자 모양이 없으면 그 글자는 안 나옵니다.

1. `gen_rbx.py` 맨 위의 `LANG_FONTS`에 언어를 한 줄 추가합니다. 쓸 TTF 글꼴과 크기를 정합니다.
   ```python
   'ja': {'main': NOTO_CJK + ':0', 'small': None, 'probe': None, 'sizes': {}},
   ```
   (정확한 모양은 `ko` 항목을 참고하세요. 등록하지 않으면 기본 글꼴이 쓰입니다.)
2. 만들면서 확인합니다.
   ```
   python3 gen_rbx.py --lang ja --verify-dir /tmp/v
   ```
   - `data/fonts/ja/`에 `.rbx` 6개가 생깁니다. `/tmp/v`에는 카메라 화면과 같은 미리보기가 저장되니 눈으로 확인하세요.
   - 번역에 쓴 글자가 글꼴에 없으면 `U+XXXX` 목록을 보여 주고 멈춥니다. 다른 글꼴로 바꾸세요.
3. 필요한 패키지: `python3-pil`(Pillow), `python3-fonttools`, `fonts-noto-cjk`.
4. 카드에는 `.rbx`를 `ML/FONTS/`에 넣습니다. 없으면 메뉴가 영어로 나옵니다.
5. 예전 카드에 남은 `ML/FONTS/*.KOX`는 이제 쓰지 않으니 지워도 됩니다.

## 빌드

저장소 맨 위에서 시작합니다(`tools/i18n`이 아닙니다).

```
cd ~/ml_src/platform/200D.101
make clean && make ARM_BINPATH=/opt/arm-none-eabi-12.3/bin ML_LANG=ko -j4
```

- 결과물은 `build/magiclantern.zip`입니다. 별도의 `zip` 명령은 없습니다.
- 언어 변수 이름은 `ML_LANG`입니다(`LANG`은 셸 설정과 겹쳐서 쓰지 않습니다). 기본값은 `en`(영어)입니다.
- 언어를 바꿔 다시 빌드할 때는 꼭 `make clean`을 먼저 하세요.
- 없는 언어 코드를 쓰면 `gen_strings: no translation file`이라는 메시지와 함께 빌드가 멈춥니다.
- 카드에 넣을 때 `autoexec.bin`과 `ML/modules/200D_101.sym`은 항상 같이 교체해야 합니다.

## 테스트

```
cd tools/i18n
python3 -m unittest discover -s tests -v
```

모두 통과해야 합니다. 도구를 고친 뒤에는 꼭 돌려 보세요.

## 알려진 한계

- 번역이 전부 라틴 문자(기존 폰트 안의 글자)만 쓰는 언어(독일어·프랑스어 등)는 아직 안 됩니다. 글자 파일(`.rbx`)이 없으면 영어로 돌아가는 구조라서, 이런 언어는 번역이 적용되지 않습니다.
- U+FFFF를 넘는 글자(이모지 등)는 쓸 수 없습니다.
