"use client";

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from 'next/navigation';
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spacer } from '@/components/ui/spacer';

export default function ChatPage() {
  const [prompt, setPrompt] = useState<string>("");
  const [response, setResponse] = useState<string>("");
  const [mriUrl, setMriUrl] = useState<string | null>(null);
  const [initialContext, setInitialContext] = useState<any>(null);
  const { toast } = useToast();
  const router = useRouter();

  useEffect(() => {
    const analysisResult = localStorage.getItem('analysisResult');
    if (analysisResult) {
      const parsed = JSON.parse(analysisResult);
      setMriUrl(`https://${process.env.NEXT_PUBLIC_S3_BUCKET}.s3.amazonaws.com/${parsed.image_file}`);
      setInitialContext(parsed);
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
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setResponse(data.response);

    } catch (error) {
      console.error('Chat error:', error);
      toast({
        title: "Error getting response",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="chat"> {}
        <TabsList>
          <TabsTrigger 
            value="upload" 
            onClick={() => router.push('/')}
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
            onClick={() => router.push('/history')}
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            History
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <Spacer axis="vertical" size={50} />
      <h1 className="text-4xl font-bold mb-4">MRI Analysis</h1>
      <Spacer axis="vertical" size={25} />

      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>AI-Powered Chatbot</CardTitle>
          <CardDescription>Ask any question about the scan.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Textarea
            placeholder="Enter your prompt here..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <Button onClick={handleChatSubmit}>
            Submit Prompt
          </Button>
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
