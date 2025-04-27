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
  const [timestamp, setTimestamp] = useState<string | null>(null);   // <- already present
  const { toast } = useToast();
  const router = useRouter();

  /* -------------------------------------------------------------------- */
  /*  Load MRI image + timestamp from either History click or new upload  */
  /* -------------------------------------------------------------------- */
  useEffect(() => {
    const histItem = localStorage.getItem("selectedHistoryItem");
    if (histItem) {
      const parsed = JSON.parse(histItem);
      setMriUrl(parsed.mri_url);
      setTimestamp(parsed.timestamp);
      return;
    }

    const res = localStorage.getItem("analysisResult");
    if (res) {
      const parsed = JSON.parse(res);
      setMriUrl(parsed.image_url);
      setTimestamp(parsed.timestamp);
    }
  }, []);

  /* -------------------------------------------------------------------- */
  /*  NEW handleChatSubmit —> now sends {prompt, timestamp} in the body   */
  /* -------------------------------------------------------------------- */
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
      /* ---------- build request body ---------- */
      const body: Record<string, any> = { prompt: prompt.trim() };
      if (timestamp) body.timestamp = timestamp;      // ← pass it along

      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

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

  /* -------------------------------------------------------------------- */
  /*  UI (unchanged)                                                      */
  /* -------------------------------------------------------------------- */
  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      {/* … Tabs, MRI image, and card markup stay exactly the same … */}
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

      {mriUrl && (
        <div className="flex justify-center w-full mb-8">
          <img
            src={mriUrl}
            alt="MRI Scan"
            className="w-60 h-60 object-cover rounded-lg shadow-lg"
          />
        </div>
      )}

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

      <p className="text-xs absolute bottom-2 right-2">Powered by NeuroAccess</p>
    </div>
  );
}
