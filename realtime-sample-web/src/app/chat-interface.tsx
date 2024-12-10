"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff, Power } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Player, Recorder } from "@/lib/audio";

interface ContentMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
}

interface StatusMessage {
  type: "status";
  content: string;
}

type Message = ContentMessage | StatusMessage;

interface TextDelta {
  id: string;
  type: "text_delta";
  delta: string;
}

interface Transcription {
  id: string;
  type: "transcription";
  text: string;
}

interface UserMessage {
  id: string;
  type: "user_message";
  text: string;
}

interface SpeechStarted {
  type: "control";
  action: "speech_started";
}

interface Connected {
  type: "control";
  action: "connected";
  greeting: string;
}

interface TextDone {
  type: "control";
  action: "text_done";
  id: string;
}

type ControlMessage = SpeechStarted | Connected | TextDone;

type WSMessage = TextDelta | Transcription | UserMessage | ControlMessage;

function isValidURL(url: string) {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

const ChatInterface = () => {
  const [endpoint, setEndpoint] = useState("ws://localhost:8000/realtime");
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [validEndpoint, setValidEndpoint] = useState(true);
  const audioPlayerRef = useRef<Player | null>(null);
  const audioRecorderRef = useRef<Recorder | null>(null);
  const webSocketClient = useRef<WebSocket | null>(null);


  const initializeWebSocket = async () => {
    if (audioPlayerRef.current === null) {
      audioPlayerRef.current = new Player();
      await audioPlayerRef.current.init(24000);
    }

    const socket = new WebSocket(new URL(endpoint));
    socket.binaryType = "arraybuffer";

    socket.onopen = () => { }
    socket.onerror = () => { }
    socket.onmessage = (ev: MessageEvent) => {
      const data = ev.data;
      if (data instanceof ArrayBuffer) {
        console.log("binary")
        audioPlayerRef.current?.play(new Int16Array(data));
      } else {
        const data = JSON.parse(ev.data) as WSMessage;
        console.log(data)
        switch (data.type) {
          case "transcription":
            setMessages(current => {
              console.log(current, "transcription")
              return ([
                ...current,
                {
                  id: data.id,
                  type: "user",
                  content: data.text,
                },
              ])
            });
            break;
          case "text_delta":
            setMessages((current) => {
              console.log(current, data.delta)
              const idx = current.findIndex((m) => m.type === "assistant" && m.id === data.id);
              if (idx === -1) {
                return [...current, {
                  id: data.id,
                  type: "assistant",
                  content: data.delta,
                }];
              } else {
                if (!current[idx].content.endsWith(data.delta)) {
                  current[idx].content += data.delta;
                }
                return current.slice(0);
              }
            });
            break;
          case "control":
            if (data.action === "connected") {
              setMessages(current => ([
                ...current,
                {
                  type: "status",
                  content: data.greeting,
                }
              ]));
            } else if (data.action === "speech_started") {
              audioPlayerRef.current?.clear();
            }
            break;

          default:
            break;
        }
      }
    }

    webSocketClient.current = socket;
  };

  const handleConnect = async () => {
    if (isConnected) {
      await disconnect();
    } else {
      setIsConnecting(true);
      initializeWebSocket();
      setIsConnecting(false);
      setIsConnected(true);
      // receiveLoop();
    }
  };

  const disconnect = async () => {
    console.log("Disconnecting...");
    setIsConnected(false);
    if (isRecording) {
      toggleRecording();
    }
    audioRecorderRef.current?.stop();
    await audioPlayerRef.current?.clear();
    await webSocketClient.current?.close();
    webSocketClient.current = null;
  };




  const sendMessage = async () => {
    if (currentMessage.trim() && webSocketClient.current) {
      const message = {
        type: "user_message",
        text: currentMessage,
      };
      setMessages([
        ...messages,
        {
          id: Math.random().toString(36),
          type: "user",
          content: currentMessage,
        },
      ]);
      setCurrentMessage("");
      await webSocketClient.current.send(JSON.stringify(message));
    }
  };

  const toggleRecording = async () => {
    if (!isRecording && webSocketClient.current) {
      try {
        if (audioRecorderRef.current === null) {
          audioRecorderRef.current = new Recorder(async (buffer) => {
            await webSocketClient.current?.send(buffer);
          });
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            sampleRate: 24000,
          }
        });
        await audioRecorderRef.current.start(stream);
        setIsRecording(true);
      } catch (error) {
        console.error("Failed to start recording:", error);
      }
    } else if (audioRecorderRef.current !== null) {
      try {
        await audioRecorderRef.current.stop();
        audioRecorderRef.current = null;
        setIsRecording(false);
      } catch (error) {
        console.error("Failed to stop recording:", error);
      }
    }
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  const validateEndpoint = (endpoint: string) => {
    setEndpoint(endpoint);
    setValidEndpoint(isValidURL(endpoint));
  };

  return (
    <div className="flex h-screen">
      {/* Parameters Panel */}
      <div className="w-80 bg-gray-50 p-4 flex flex-col border-r">
        <div className="flex-1 overflow-y-auto">
          <div className="text-lg font-semibold mb-2">
            Connection Settings
          </div>
          <div className="space-y-4">
            <Input
              placeholder="Endpoint"
              value={endpoint}
              onChange={(e) => validateEndpoint(e.target.value)}
              disabled={isConnected}
            />
          </div>
        </div>

        {/* Connect Button */}
        <Button
          className="mt-4"
          variant={isConnected ? "destructive" : "default"}
          onClick={handleConnect}
          disabled={isConnecting || !validEndpoint}
        >
          <Power className="w-4 h-4 mr-2" />
          {isConnecting
            ? "Connecting..."
            : isConnected
              ? "Disconnect"
              : "Connect"}
        </Button>
      </div>

      {/* Chat Window */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 p-4 overflow-y-auto">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`mb-4 p-3 rounded-lg ${message.type === "user"
                ? "bg-blue-100 ml-auto max-w-[80%]"
                : "bg-gray-100 mr-auto max-w-[80%]"
                }`}
            >
              {message.content}
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Input
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              placeholder="Type your message..."
              onKeyUp={(e) => e.key === "Enter" && sendMessage()}
              disabled={!isConnected}
            />
            <Button
              variant="outline"
              onClick={toggleRecording}
              className={isRecording ? "bg-red-100" : ""}
              disabled={!isConnected}
            >
              {isRecording ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </Button>
            <Button onClick={sendMessage} disabled={!isConnected}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
