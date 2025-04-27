"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spacer } from "@/components/ui/spacer";

export default function ChatPage() {
  const [prompt, setPrompt] = useState<string>("");
  const [response, setResponse] = useState<string>("");
  const [mriUrl, setMriUrl] = useState<string | null>(null);
  const [timestamp, setTimestamp] = useState<string | null>(null);
  const { toast } = useToast();
  const router = useRouter();

  useEffect(() => {
    const histItem = localStorage.getItem("selectedHistoryItem");
    if (histItem) {
      const parsed = JSON.parse(histItem);
      setMriUrl(parsed.mri_url);
      setTimestamp(parsed.timestamp);
      return;
    }

    const latestUpload = localStorage.getItem("analysisResult");
    if (latestUpload) {
      const parsed = JSON.parse(latestUpload);
      setMriUrl(parsed.image_url);
      setTimestamp(parsed.timestamp);
    }
  }, []);

  const handleChatSubmit = async () => {
    if (!prompt.trim()) {
      toast({
        title: "Empty prompt",
        description: "Please enter a question to ask the chatbot.",
        variant: "destructive",
      });
      return;
    }

    try {
      const body = {
        prompt: prompt.trim(),
        timestamp,
      };

      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setResponse(data.response);
    } catch (err) {
      console.error("Chat error:", err);
      toast({
        title: "Error getting response",
        description:
          err instanceof Error ? err.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="chat">
        <TabsList>
          <TabsTrigger
            value="upload"
            onClick={() => router.push("/")}
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            Upload Images
          </TabsTrigger>
          <TabsTrigger
            value="chat"
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            Query
          </TabsTrigger>
          <TabsTrigger
            value="history"
            onClick={() => router.push("/history")}
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            History
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <Spacer axis="vertical" size={50} />
      <h1 className="text-4xl font-bold mb-4">MRI Analysis</h1>

      {/* -------------------------- MRI preview or placeholder -------------------------- */}
      {mriUrl ? (
        <div className="flex justify-center w-full mb-8">
          <img
            src={mriUrl}
            alt="MRI Scan"
            className="w-60 h-60 object-cover rounded-lg shadow-lg"
          />
        </div>
      ) : (
        <p className="mb-8 italic text-muted-foreground">
          No image uploaded yet. Go to{" "}
          <span className="font-semibold">Upload Images</span> or pick one from{" "}
          <span className="font-semibold">History</span>.
        </p>
      )}

      {/* -------------------------- Chat card ------------------------------------------ */}
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>AI-Powered Chatbot</CardTitle>
          <CardDescription>Ask any question about the scan.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Textarea
            placeholder="Enter your prompt here…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <Button onClick={handleChatSubmit}>Submit Prompt</Button>

          {response && (
            <div className="rounded-md border p-4 bg-white text-black">
              <p>{response}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs fixed bottom-2 right-2">Powered by Neurolytics</p>
    </div>
  );
}
