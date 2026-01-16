export default class RealtimeAudio {
  private container: HTMLElement;
  private realtimeAudioElement: HTMLElement;
  private final: string = "";
  private incoming: string = "";

  constructor(container: HTMLElement) {
    this.container = container;
    this.realtimeAudioElement = document.createElement("div");
    this.realtimeAudioElement.className = "record-realtime-audio";
    this.container.appendChild(this.realtimeAudioElement);
  }

  public update(newTranscript: string, isFinal: boolean): void {
    this.realtimeAudioElement.innerHTML = "";

    if (isFinal) {
      this.final += newTranscript + ". ";
      this.incoming = "";
    } else {
      this.incoming = this.merge(this.incoming, newTranscript);
    }

    this.realtimeAudioElement.innerHTML = `<div class="realtime-transcript">
                                            Realtime Transcript: 
                                            <span class="final"> ${this.final} </span>
                                            <span class="incoming">${this.incoming}</span> 
                                            </div>`;
  }

  public clear(): void {
    this.final = "";
    this.incoming = "";
    this.realtimeAudioElement.innerHTML = "";
  }

  public merge(oldText: string, newText: string): string {
    oldText = oldText.trim();
    newText = newText.trim();

    if (oldText === "") {
      return newText;
    }

    if (newText === "") {
      return oldText;
    }

    return "hello there";
  }
}
