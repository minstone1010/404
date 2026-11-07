import { createContext, useCallback, useContext, useMemo, useReducer, useRef, useState, type ReactNode } from 'react';
import { complaints as reviewComplaints, currentUser, initialFiles } from './data/mock';
import { autoSamples } from './data/samples';
import type { TaxonomyKey, TaxonomyValue } from './data/taxonomy';
import type { Complaint, Delivery, UploadedFile } from './types';

type Dept = TaxonomyValue<'dept'>;

interface State {
  files: UploadedFile[];
  complaints: Complaint[];
  deliveries: Partial<Record<Dept, Delivery>>;
  senderName: string;
  /** 담당자가 고친 메일 본문. null이면 기본 인사말을 써요. */
  mailBody: string | null;
}

type Action =
  | { type: 'addFiles'; files: UploadedFile[] }
  | { type: 'updateFile'; id: string; patch: Partial<UploadedFile> }
  | { type: 'removeFile'; id: string }
  | { type: 'resolveColumns'; id: string; column: string }
  | { type: 'setClass'; id: string; key: TaxonomyKey; value: string }
  | { type: 'approve'; ids: string[] }
  | { type: 'sendDept'; dept: Dept; delivery: Delivery }
  | { type: 'setSender'; name: string }
  | { type: 'setMailBody'; body: string | null };

/** 기본 메일 인사말 — 담당자가 고치면 다음 부서 메일에도 그대로 써요 */
export const defaultMailBody = (name: string) =>
  `안녕하세요.\n코레일 민원 VOC 담당자 ${name || 'OOO'}입니다.\n정리한 민원 보내드립니다.`;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'addFiles':
      return { ...state, files: [...state.files, ...action.files] };
    case 'updateFile':
      return { ...state, files: state.files.map((f) => (f.id === action.id ? { ...f, ...action.patch } : f)) };
    case 'removeFile':
      return { ...state, files: state.files.filter((f) => f.id !== action.id) };
    case 'resolveColumns':
      // 실제로는 고른 열 이름을 서버에 보내 다시 읽어요 (PUT /files/{id}/columns)
      return {
        ...state,
        files: state.files.map((f) =>
          f.id === action.id ? { ...f, error: undefined, missing: undefined, count: f.count ?? 1240 } : f,
        ),
      };
    case 'setClass':
      return {
        ...state,
        complaints: state.complaints.map((c) =>
          c.id === action.id
            ? {
                ...c,
                classification: { ...c.classification, [action.key]: action.value },
                flags: c.flags.filter((f) => f !== action.key),
              }
            : c,
        ),
      };
    case 'approve':
      return {
        ...state,
        complaints: state.complaints.map((c) =>
          action.ids.includes(c.id) && c.status === 'review' ? { ...c, status: 'approved' } : c,
        ),
      };
    case 'sendDept':
      // 그 부서로 정리된(승인된) 민원을 모두 발송 완료로 바꿔요
      return {
        ...state,
        deliveries: { ...state.deliveries, [action.dept]: action.delivery },
        complaints: state.complaints.map((c) =>
          c.classification.dept === action.dept && c.status === 'approved' ? { ...c, status: 'sent' } : c,
        ),
      };
    case 'setSender':
      return { ...state, senderName: action.name };
    case 'setMailBody':
      return { ...state, mailBody: action.body };
  }
}

interface Store extends State {
  dispatch: React.Dispatch<Action>;
  toast: string | null;
  showToast: (message: string) => void;
}

const StoreContext = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    files: initialFiles,
    complaints: [...reviewComplaints, ...autoSamples],
    deliveries: {},
    senderName: currentUser.name,
    mailBody: null,
  });
  const [toast, setToast] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const showToast = useCallback((message: string) => {
    setToast(message);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToast(null), 2800);
  }, []);

  const value = useMemo(() => ({ ...state, dispatch, toast, showToast }), [state, toast, showToast]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore는 StoreProvider 안에서만 쓸 수 있어요');
  return store;
}
