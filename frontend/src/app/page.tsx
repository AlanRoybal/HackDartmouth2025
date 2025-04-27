"use client";

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import logo from '@/assets/images/NeuroAccess_logo.png';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Spacer } from '@/components/ui/spacer';
import { CenteredDivider } from "@/components/ui/divider";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function Home() {
  const router = useRouter();
  const [image, setImage] = useState<string | null>(null);
  const { toast } = useToast();
  const [chatEnabled, setChatEnabled] = useState(false);

  useEffect(() => {
      localStorage.setItem('uploadedImage', JSON.stringify(image));
    }, [image]);

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

    const deleteImage = () => {
      setImage(null);
    };

    const handleSubmit = async () => {
      if (!image) {
        toast({
          title: "No images uploaded",
          description: "Please upload at least one image to enable the chatbot.",
        });
        return;
      }
    
      try {
        const base64Response = await fetch(image);
        const blob = await base64Response.blob();
        const formData = new FormData();
        formData.append('file', blob, 'mri_scan.jpg');
    
        // Show loading page
        router.push('/loading');
    
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
    
        // Save result to localStorage
        localStorage.setItem('analysisResult', JSON.stringify(analysisResult));
        
        // Now go to /chat
        router.push('/chat');
    
      } catch (error) {
        console.error('Error:', error);
        toast({
          title: "Error analyzing image",
          description: error instanceof Error ? error.message : "Unknown error occurred",
          variant: "destructive",
        });
    
        // In case of error, go back to landing page
        router.push('/');
      }
    };    

  // output
  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="upload">
        <TabsList>
          <TabsTrigger value="upload" onClick={() => router.push('/')} className="text-black data-[state=active]:bg-black data-[state=active]:text-white">
            Upload Images
          </TabsTrigger>
          <TabsTrigger value="chat" onClick={() => router.push('/chat')} className="text-black data-[state=active]:bg-black data-[state=active]:text-white">
            Query
          </TabsTrigger>
          <TabsTrigger value="history" className="text-black data-[state=active]:bg-black data-[state=active]:text-white">
            History
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <Spacer axis="vertical" size={50} />

      <img
        src={logo.src}
        alt="Logo"
        className="mb-6"
        style={{ width: '180px', height: '130px' }}
      />
      <h1 className="text-4xl font-bold mb-4">NeuroAccess</h1>
      <p className="text-lg mb-8">Neuro-oncology unlocked for anyone, everyone.</p>

      <Tabs defaultValue="upload" className="w-full max-w-2xl mb-8">
        <CenteredDivider />
        <Spacer axis="vertical" size={20} />
        <Spacer axis="vertical" size={20} />
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
    </div>
  );
}
