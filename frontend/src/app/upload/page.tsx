"use client";

import { useState, useCallback, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from 'next/navigation';
import { Spacer } from '@/components/ui/spacer';
import logo from '@/assets/images/NeuroAccess_logo.png';

export default function UploadPage() {
  const [image, setImage] = useState<string | null>(null);
  const [chatEnabled, setChatEnabled] = useState(false);
  const [prompt, setPrompt] = useState<string>(() => {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('promptText') || "";
    }
    return "";
  });
  const [response, setResponse] = useState<string>(() => {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('chatResponse') || "";
    }
    return "";
  });
  const { toast } = useToast();
  const router = useRouter();

  useEffect(() => {
    localStorage.setItem('uploadedImage', JSON.stringify(image));
  }, [image]);
  
  useEffect(() => {
    localStorage.setItem('promptText', prompt);
  }, [prompt]);

  useEffect(() => {
    localStorage.setItem('chatResponse', response);
  }, [response]);

  const handleImageUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files) {
      return;
    }

    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) {
        setImage(e.target.result.toString());
      }
    };
    reader.readAsDataURL(file);
  }, []);

  const handleSubmit = async () => {
    if (!image) {
      toast({
        title: "No images uploaded",
        description: "Please upload at least one image to enable the chatbot.",
      });
      return;
    }

    try {
      // Convert base64 to blob
      const base64Response = await fetch(image);
      const blob = await base64Response.blob();

      // Create FormData and append file
      const formData = new FormData();
      formData.append('file', blob, 'mri_scan.jpg');

      // Upload to backend
      const response = await fetch('http://localhost:5000/analyze_mri', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const analysisResult = await response.json();
      
      if (analysisResult.error) {
        throw new Error(analysisResult.error);
      }

      setChatEnabled(true);
      toast({
        title: "Analysis complete",
        description: "You can now interact with the chatbot.",
      });

      // Store analysis result
      localStorage.setItem('analysisResult', JSON.stringify(analysisResult));

    } catch (error) {
      console.error('Error:', error);
      toast({
        title: "Error analyzing image",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  };

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

  const deleteImage = () => {
    setImage(null);
  };

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="upload" className="w-full max-w-2xl mb-8">
        <TabsList>
          <TabsTrigger value="upload">Upload Images</TabsTrigger>
          <TabsTrigger value="history" onClick={() => router.push('/history')}>View History</TabsTrigger>
        </TabsList>

        <Spacer axis="vertical" size={50} />

          <h1 className="text-4xl font-bold mb-4">NeuroScan Upload</h1>

          <Spacer axis="vertical" size={16} />

          <p className="text-lg mb-8">Upload MRI scans to interact with the AI-powered chatbot</p>

          <div className="mb-8">
            <Input
              type="file"
              
              accept="image/*"
              onChange={handleImageUpload}
              className="mb-4"
            />
          {image && (
          <div className="flex flex-wrap gap-4">
              <div className="relative">
                  <img src={image} alt="Uploaded Image" className="w-32 h-32 object-cover rounded-md shadow-md" />
                  <Button
                    onClick={deleteImage}
                    variant="ghost"
                    className="absolute top-0 right-0 p-1 text-white rounded-full hover:bg-gray-600 focus-visible:ring-0 focus-visible:ring-offset-0 focus:outline-none"
                    aria-label="Delete Image"
                  >
                    X
                  </Button>
              </div>
          </div>
          )}
          </div>

          <Button
            onClick={handleSubmit}
            disabled={chatEnabled}
            className="mb-8 bg-primary text-primary-foreground hover:bg-primary/80"
          >
            {chatEnabled ? "Processed" : "Submit Images"}
          </Button>
      </Tabs>

      {chatEnabled && (
        <Card className="w-full max-w-2xl">
          <CardHeader>
            <CardTitle>AI-Powered Chatbot</CardTitle>
            <CardDescription>Ask any question about the uploaded images.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-col space-y-2">
              <Textarea
                placeholder="Enter your prompt here..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
              <Button
                onClick={handleChatSubmit}
                className="bg-accent text-accent-foreground hover:bg-accent/80"
              >
                Submit Prompt
              </Button>
            </div>
            {response && (
              <div className="rounded-md border p-4 bg-white text-black">
                <p>{response}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <p className="text-xs absolute bottom-2 right-2">Powered by NeuroAccess</p>
    </div>
  );
}
