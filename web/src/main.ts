import './style.css'
import Recorder from './recorder.ts'

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <div>
    <h1>Mood Detection</h1>
    <div id="recorder-container"></div>
  </div>
`;

const recorderContainer = document.querySelector<HTMLDivElement>('#recorder-container')!;
new Recorder(recorderContainer);