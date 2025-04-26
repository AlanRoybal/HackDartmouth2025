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
  const [images, setImages] = useState<string[]>([]);
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
    localStorage.setItem('uploadedImages', JSON.stringify(images));
  }, [images]);

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

    const files: FileList = event.target.files;
    const newImages: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const reader = new FileReader();

      reader.onload = (e) => {
        if (e.target?.result) {
          newImages.push(e.target.result.toString());
          if (newImages.length === files.length) {
            setImages((prevImages) => [...prevImages, ...newImages]);
          }
        }
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const handleSubmit = async () => {
    if (images.length === 0) {
      toast({
        title: "No images uploaded",
        description: "Please upload at least one image to enable the chatbot.",
      });
      return;
    }
    setChatEnabled(true);
    toast({
      title: "You can now interact with the chatbot.",
    });
  };

  const handleChatSubmit = async () => {
    const newResponse = `Response to prompt: ${prompt}`;
    setResponse(newResponse);
  };

  const deleteImage = (index: number) => {
    setImages((prevImages) => {
        const newImages = [...prevImages];
        newImages.splice(index, 1);
        return newImages;
    });
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
              multiple
              accept="image/*"
              onChange={handleImageUpload}
              className="mb-4"
            />
            <div className="flex flex-wrap gap-4">
              {images.map((image, index) => (
                <div key={index} className="relative">
                    <img src={image} alt={`Uploaded Image ${index + 1}`} className="w-32 h-32 object-cover rounded-md shadow-md" />
                    <Button
                      onClick={() => deleteImage(index)}
                      variant="ghost"
                      className="absolute top-0 right-0 p-1 text-white rounded-full hover:bg-gray-600 focus-visible:ring-0 focus-visible:ring-offset-0 focus:outline-none"
                      aria-label="Delete Image"
                    >
                      X
                    </Button>
                </div>
              ))}
            </div>
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
