# 기존 EC2 배포에 CI/CD 적용하기

기존 ECR/EC2/SSM을 그대로 사용한다. 코드를 main에 반영하면 테스트 성공 후 새 이미지를 배포한다.
이 문서 작성 과정에서는 AWS 배포를 실행하지 않았다.

## 실행 흐름

1. main 대상 PR: Python 문법 검사, API·정책·배포 스크립트 테스트, Spring 테스트.
2. main push 또는 main에서 수동 실행: 같은 검사 후 두 Docker 이미지 빌드 및 ECR push.
3. 현재 커밋의 `compose.prod.yml`과 배포 스크립트를 SSM으로 전달.
4. EC2에서 모델 경로/Compose 지원 옵션 확인, ECR 로그인, 이미지 pull.
5. 서버 `.env`의 `IMAGE_TAG`/`ECR_REGISTRY`만 갱신하고 Compose 파일 교체.
6. 모델 세 개가 준비될 때까지 기다리고 웹 `http://127.0.0.1:8080/` 응답 확인.
7. SSM의 `Success`와 종료 코드 0을 모두 확인한 경우에만 Actions 성공.

기존 `VT_API_KEY`, 모델 디렉터리, OCR 캐시 볼륨은 유지한다. 배포는 직렬 실행하며
EC2 파일 잠금으로 이전 SSM 작업이 남아 있을 때의 중복 실행도 막는다.
모델 가중치는 GitHub Actions에서 전송하지 않는다.

## GitHub에서 확인할 설정

Repository → Settings → Secrets and variables → Actions:

| Secret | 값 |
| --- | --- |
| `AWS_ROLE_ARN` | 기존 GitHub OIDC 배포 역할 ARN |
| `EC2_INSTANCE_ID` | 기존 운영 EC2 인스턴스 ID |

리전은 `ap-northeast-2`, ECR 저장소는 `smishing-checker-web`, `smishing-checker-fastapi`다.
OIDC 역할은 main 브랜치에서 AssumeRole 가능해야 한다. 기존 ECR push 권한과
대상 인스턴스/`AWS-RunShellScript`의 `ssm:SendCommand`, `ssm:GetCommandInvocation` 권한을 확인한다.
EC2 인스턴스 역할에는 기존 SSM 연결 및 ECR pull 권한이 필요하다.
PR 테스트에는 AWS 자격 증명을 사용하지 않는다.
main 보호 규칙에서 `Test API and web`을 필수 상태 검사로 지정하면 테스트 실패 PR의 병합도 막을 수 있다.

## EC2에서 한 번 확인할 조건

SSM이 실행하는 계정에서 다음 명령이 성공해야 한다. 서버의 비밀값을 출력할 필요는 없다.

```bash
cd /opt/smishing
test -f .env
test -s models/text/config.json
test -s models/url/model/config.json
test -s models/url/internal_test_metrics.json
docker compose version
docker compose up --help | grep -- --wait-timeout
command -v aws curl flock base64
```

`models/text`와 `models/url/model`에는 config뿐 아니라 기존 토크나이저·가중치 파일도 있어야 한다.
스크립트는 시작 시 config/metrics 존재를 먼저 확인하고 실제 모델 로딩은 컨테이너에서 검증한다.
EC2에는 Bash, AWS CLI, Docker Compose v2(`--wait`, `--wait-timeout` 지원), curl, flock이 필요하다.
기존 배포의 `/opt/smishing`, 8080 포트, CPU 이미지 구성을 전제로 한다.
Compose 헬스체크는 OCR·문자·URL 모델의 로딩 상태를 확인한다.

## 반영 및 성공 확인

변경 파일을 커밋하고 main에 push하거나 PR을 병합한다.
Actions → `CI and Deploy to AWS` → `Test API and web`, `Build and deploy`가 모두 성공했는지 확인한다.
수동 재실행은 main에서 `Run workflow`를 사용한다.
배포 단계 마지막에 `Deployment verified: <커밋 SHA>`가 있어야 한다.

서버 확인:

```bash
cd /opt/smishing
docker compose --env-file .env -f compose.prod.yml ps
docker compose --env-file .env -f compose.prod.yml exec -T fastapi \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
curl -f http://127.0.0.1:8080/
```

`fastapi`가 healthy이고 `ocr.loaded`, `textModel.loaded`, `urlModel.loaded`가 모두 true여야 한다.
외부 도메인/HTTPS/로드밸런서는 이 내부 검사와 별도로 실제 서비스 주소에서 확인한다.
이미지 업로드 분석도 한 번 실행해 운영 모델의 추론을 확인한다.

## 실패 시

Actions에 출력된 SSM command ID와 단계 로그를 확인한다.
pull/기동/HTTP 검사 오류를 숨기지 않고 실패로 전달하며, 기동 후 오류에는 컨테이너 로그를 출력한다.
SSM 명령의 최대 실행 시간은 35분, Actions의 결과 대기는 40분이다.
모델 준비 대기는 15분이며 최초 OCR 다운로드나 서버 자원 부족으로 실패할 수 있다.

```bash
cd /opt/smishing
docker compose --env-file .env -f compose.prod.yml logs --tail 100 fastapi web
```

pull 실패 시 기존 설정과 컨테이너는 그대로다. 기동 도중 실패하면 일부 컨테이너는
새 버전일 수 있다. 자동 롤백과 무중단 배포는 제공하지 않는다.
교체 직전 설정은 `compose.prod.yml.previous`, `.env.previous`에 저장한다.
이 백업은 **직전 시도 전의 상태**이므로 여러 번 재시도했다면 정상 버전인지 먼저 확인한다.
정상 버전의 백업임을 확인한 경우 서버에서 다음과 같이 복구할 수 있다.

```bash
cd /opt/smishing
cp compose.prod.yml.previous compose.prod.yml
cp .env.previous .env
docker compose --env-file .env -f compose.prod.yml pull
docker compose --env-file .env -f compose.prod.yml up -d --wait --wait-timeout 900
curl -f http://127.0.0.1:8080/
```

참고: [`docker compose up --wait`](https://docs.docker.com/reference/cli/docker/compose/up/)는
running/healthy 상태까지 기다린다. 기존 [AWS CLI 기본 waiter](https://docs.aws.amazon.com/cli/latest/reference/ssm/wait/command-executed.html)는
약 100초만 기다리므로 모델 배포를 위해 상태 조회 루프로 교체했다.
