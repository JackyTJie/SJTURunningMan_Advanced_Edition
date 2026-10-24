import { createRoot } from 'react-dom/client';

import '@material/web/button/filled-button.js';
import '@material/web/button/filled-tonal-button.js';
import '@material/web/button/outlined-button.js';
import '@material/web/button/text-button.js';
import '@material/web/checkbox/checkbox.js';
import '@material/web/dialog/dialog.js';
import '@material/web/divider/divider.js';
import '@material/web/icon/icon.js';
import '@material/web/iconbutton/icon-button.js';
import '@material/web/iconbutton/outlined-icon-button.js';
import '@material/web/list/list.js';
import '@material/web/list/list-item.js';
import '@material/web/progress/circular-progress.js';
import '@material/web/progress/linear-progress.js';
import '@material/web/select/outlined-select.js';
import '@material/web/select/select-option.js';
import '@material/web/switch/switch.js';
import '@material/web/textfield/outlined-text-field.js';
import '@material/web/labs/card/elevated-card.js';
import '@material/web/labs/card/outlined-card.js';
import '@material/web/labs/navigationdrawer/navigation-drawer.js';
import '@material/web/labs/segmentedbutton/outlined-segmented-button.js';
import '@material/web/labs/segmentedbuttonset/outlined-segmented-button-set.js';

import './styles/tokens.css';
import './styles/global.css';
import { App } from './App';

if ('__TAURI_INTERNALS__' in window && navigator.userAgent.includes('Macintosh')) {
  document.documentElement.dataset.platform = 'macos';
}

const container = document.getElementById('root');
if (!container) throw new Error('Missing #root');
createRoot(container).render(<App />);
