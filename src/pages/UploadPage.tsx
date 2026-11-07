import { useRef, useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import uploadIcon from '../assets/icon-upload.svg';
import { Button, Chip, fmt, PageHeader, Select } from '../components/ui';
import { DUPLICATE_COUNT } from '../data/mock';
import { REQUIRED_HEADERS } from '../data/outputColumns';
import { readVocFile } from '../lib/excel';
import { useStore } from '../store';
import type { UploadedFile } from '../types';

const missingMessage = (missing: string[]) =>
  `${missing.map((m) => `"${m}"`).join(', ')} 열을 찾지 못했어요. 어느 열인지 골라주면 같이 분석해요.`;

/** V3 · 1 파일 올리기 (Figma 87:202) */
export function UploadPage() {
  const { files, dispatch, showToast } = useStore();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [mapping, setMapping] = useState<{ id: string; column: string } | null>(null);

  const ready = files.filter((f) => !f.error && f.count !== null);
  const total = files.reduce((sum, f) => sum + (f.count ?? 0), 0);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const picked = Array.from(list).filter((f) => /\.xlsx$/i.test(f.name));
    if (picked.length === 0) {
      showToast('.xlsx 파일만 올릴 수 있어요');
      return;
    }
    const added: UploadedFile[] = picked.map((f) => ({ id: `${f.name}-${f.lastModified}-${Math.random()}`, name: f.name, count: null }));
    dispatch({ type: 'addFiles', files: added });

    // 브라우저에서 바로 머리글과 건수를 확인해요. 실제 서비스에서는 서버(POST /batches)가 같은 검사를 해요.
    added.forEach((meta, i) => {
      readVocFile(picked[i])
        .then(({ count, headers, missing }) =>
          dispatch({
            type: 'updateFile',
            id: meta.id,
            patch: missing.length ? { count, headers, missing, error: missingMessage(missing) } : { count },
          }),
        )
        .catch(() =>
          dispatch({ type: 'updateFile', id: meta.id, patch: { count: 0, error: '파일을 읽지 못했어요. 암호가 걸려 있거나 손상된 파일인지 확인해 주세요.' } }),
        );
    });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    addFiles(e.dataTransfer.files);
  };

  return (
    <main className="page">
      <PageHeader
        title="민원 Excel 파일을 올려주세요"
        desc="본부·채널별 파일을 여러 개 한꺼번에 올려도 돼요. 합쳐서 한 번에 분석합니다."
      />

      <section
        className={`dropzone ${over ? 'is-over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        aria-label="파일 놓는 곳"
      >
        <img className="dropzone__icon" src={uploadIcon} width={40} height={40} alt="" />
        <div className="dropzone__text">
          <p className="dropzone__title">파일이나 폴더를 여기에 끌어다 놓으세요</p>
          <p className="dropzone__hint">
            코레일 민원 내보내기 .xlsx 여러 개 가능 · {REQUIRED_HEADERS.join('·')} 열만 있으면 돼요
          </p>
        </div>
        <Button variant="secondary" onClick={() => inputRef.current?.click()}>
          파일 추가
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          multiple
          hidden
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </section>

      <section className="card" aria-label="올린 파일 목록">
        <div className="list-head">
          <p className="list-head__title">
            올린 파일 {files.length}개 · 분석 가능 {ready.length}개 · 민원 {fmt(total)}건
          </p>
          <p className="list-head__note">같은 접수번호가 여러 파일에 있으면 하나로 합쳐요 (중복 {DUPLICATE_COUNT}건)</p>
        </div>
        {files.map((f) =>
          f.error ? (
            <div key={f.id} className="file-row file-row--error">
              <span className="file-row__icon" aria-hidden>
                ▤
              </span>
              <div className="file-row__name">
                <p>{f.name}</p>
                <p className="file-row__error">{f.error}</p>
              </div>
              {mapping?.id === f.id && f.headers?.length ? (
                <>
                  <Select
                    label={`${f.missing?.[0] ?? '질문'} 열 고르기`}
                    value={mapping.column}
                    options={f.headers}
                    onChange={(column) => setMapping({ id: f.id, column })}
                  />
                  <Button
                    onClick={() => {
                      dispatch({ type: 'resolveColumns', id: f.id, column: mapping.column });
                      setMapping(null);
                      showToast(`"${mapping.column}" 열을 ${f.missing?.[0] ?? '질문'}(으)로 읽어요`);
                    }}
                  >
                    이 열로 읽기
                  </Button>
                </>
              ) : f.headers?.length ? (
                <Button variant="secondary" onClick={() => setMapping({ id: f.id, column: f.headers![0] })}>
                  열 지정
                </Button>
              ) : (
                <button className="file-row__remove" aria-label={`${f.name} 빼기`} onClick={() => dispatch({ type: 'removeFile', id: f.id })}>
                  ✕
                </button>
              )}
            </div>
          ) : (
            <div key={f.id} className="file-row">
              <span className="file-row__icon" aria-hidden>
                ▤
              </span>
              <p className="file-row__name">{f.name}</p>
              <p className="file-row__count">{f.count === null ? '읽는 중' : `${fmt(f.count)}건`}</p>
              <Chip tone={f.count === null ? 'info' : 'ok'}>{f.count === null ? '확인 중' : '읽기 완료'}</Chip>
              <button
                className="file-row__remove"
                aria-label={`${f.name} 빼기`}
                onClick={() => dispatch({ type: 'removeFile', id: f.id })}
              >
                ✕
              </button>
            </div>
          ),
        )}
      </section>

      <div className="spacer" />

      <div className="footer-bar">
        <div className="footer-bar__hint">
          <span className="muted">특정 업무만 다시 돌려야 하나요?</span>
          <button className="link-strong" onClick={() => showToast('개별 업무 선택 화면은 다음 시안에서 이어져요')}>
            개별 업무 선택 →
          </button>
        </div>
        <Button disabled={ready.length === 0} onClick={() => navigate('/analysis')}>
          파일 {ready.length}개 분석 시작
        </Button>
      </div>
    </main>
  );
}
