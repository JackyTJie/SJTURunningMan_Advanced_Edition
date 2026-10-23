import { useRef, useState } from 'react';
import { Dialog } from '../components/Dialog';
import { useCustomEvent } from '../lib/foreign';
import type { MdCheckbox } from '../types/md';

interface ConsentDialogProps {
  open: boolean;
  onAccept: () => void;
  onQuit: () => void;
}

export function ConsentDialog({ open, onAccept, onQuit }: ConsentDialogProps) {
  const [checked, setChecked] = useState(false);
  const checkboxRef = useRef<MdCheckbox>(null);
  useCustomEvent<Event, MdCheckbox>(checkboxRef, 'change', () => {
    setChecked(checkboxRef.current?.checked ?? false);
  });

  return (
    <Dialog
      open={open}
      onClose={() => undefined}
      headline="使用承诺书"
      icon="shield"
      preventCancel
      type="alert"
      className="consent-dialog"
      actions={
        <>
          <md-text-button onClick={onQuit}>退出</md-text-button>
          <md-filled-button onClick={onAccept} disabled={!checked}>
            我承诺，进入软件
          </md-filled-button>
        </>
      }
    >
      <div className="consent-body">
        <p>在继续使用本软件前，请认真阅读并作出承诺：</p>
        <ol>
          <li>我理解本项目仅用于学习、研究和技术测试，主要用于理解运动数据记录与上传相关的技术流程。</li>
          <li>我理解项目开发者反对任何违反学校规定的使用方式。</li>
          <li>我承诺在使用前确认自己的行为符合上海交通大学校规及相关法律法规的要求。</li>
          <li>我承诺不会将本软件用于伪造运动数据、规避体育锻炼要求或其他违规操作。</li>
        </ol>
      </div>
      <label
        className="checkbox-row"
        onClick={(event) => {
          if ((event.target as HTMLElement).closest('md-checkbox')) return;
          event.preventDefault();
          const next = !checked;
          setChecked(next);
          if (checkboxRef.current) checkboxRef.current.checked = next;
        }}
      >
        <md-checkbox ref={checkboxRef} aria-label="我已阅读以上内容，并承诺不会将本软件用于任何违规操作" />
        <span>我已阅读以上内容，并承诺不会将本软件用于任何违规操作。</span>
      </label>
    </Dialog>
  );
}
