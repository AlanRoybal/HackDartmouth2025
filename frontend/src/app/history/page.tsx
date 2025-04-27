"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from 'next/navigation';
import { Spacer } from '@/components/ui/spacer';

export default function HistoryPage() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="history"> {}
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
            onClick={() => router.push('/chat')}
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            Query
          </TabsTrigger>
          <TabsTrigger 
            value="history" 
            className="text-black data-[state=active]:bg-black data-[state=active]:text-white"
          >
            History
          </TabsTrigger>
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
