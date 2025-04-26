"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from 'next/navigation';
import { Spacer } from '@/components/ui/spacer';

export default function HistoryPage() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="history" className="w-full max-w-2xl mb-8" onValueChange={(value) => {
        if (value === "upload") router.push('/upload');
      }}>
        <TabsList>
          <TabsTrigger value="history">View History</TabsTrigger>
          <TabsTrigger value="upload">Upload Images</TabsTrigger>
        </TabsList>
      </Tabs>

      <Spacer axis="vertical" size={50} />

      <h1 className="text-4xl font-bold mb-4">Prompt History</h1>
      <p className="text-lg mb-8">View your previous prompts and responses from the chatbot.</p>

      <p className="text-right">No history available yet...</p>

      <p className="text-xs absolute bottom-2 right-2">Powered by NeuroAccess</p>
    </div>
  );
}


