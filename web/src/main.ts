import "./styles/style.css";
import RecordButton from "./components/recordButton";
import RealtimeTranscript from "./components/realtimeTranscript.ts";
import AgentStatus from "./components/agentStatus.ts";
import AudioRecorder from "./audio/audioRecorder.ts";
import StreamingService from "./services/streamingService";
import { StreamingServiceHelper } from "./services/streamingServiceHelper";
import LLMPicker from "./components/llmPicker";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <div>
    <h1>Mood Detection Agent</h1>
    <div id="llm-picker-container"></div>
    <div id="record-button-container"></div>
    <div id="agent-status-container"></div>
    <div id="realtime-transcript-container"></div>
  </div>
`;

const llmPickerContainer = document.querySelector<HTMLDivElement>(
  "#llm-picker-container",
)!;

const recordButtonContainer = document.querySelector<HTMLDivElement>(
  "#record-button-container",
)!;

const agentStatusContainer = document.querySelector<HTMLDivElement>(
  "#agent-status-container",
)!;

const realtimeTranscriptContainer = document.querySelector<HTMLDivElement>(
  "#realtime-transcript-container",
)!;

const llmPicker = new LLMPicker(llmPickerContainer);
const agentStatus = new AgentStatus(agentStatusContainer);
const realtimeTranscript = new RealtimeTranscript(realtimeTranscriptContainer);

const helper = new StreamingServiceHelper(
  agentStatus,
  realtimeTranscript,
  null as any,
  null as any,
  llmPicker,
);

const streamingService = new StreamingService(
  helper.onTranscriptUpdate,
  helper.onQuestionAudio,
  helper.onQuestion,
  helper.onListening,
  helper.onAnalyzing,
  helper.onResult,
  helper.onNoResult,
  helper.onError,
  helper.onWebSocketClosed,
);

streamingService.setHelper(helper);

const audioRecorder = new AudioRecorder(streamingService);
audioRecorder.setLLMPicker(llmPicker);

const recordButton = new RecordButton(recordButtonContainer, audioRecorder);

helper["recordButton"] = recordButton;
helper["audioRecorder"] = audioRecorder;
