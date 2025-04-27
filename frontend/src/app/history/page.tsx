"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from 'next/navigation';
import { Spacer } from '@/components/ui/spacer';
import { useEffect, useState } from "react";

export default function HistoryPage() {
  const router = useRouter();
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch('http://localhost:5000/history');
        const data = await res.json();
        setHistoryItems(data);
      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs defaultValue="history">
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

      <h1 className="text-4xl font-bold mb-4">Prompt History</h1>
      <p className="text-lg mb-8">View your previous prompts and responses from the chatbot.</p>

      {loading ? (
        <p>Loading history...</p>
      ) : historyItems.length === 0 ? (
        <p className="text-right">No history available yet...</p>
      ) : (
        <div className="flex flex-col gap-8 w-full max-w-4xl">
          {historyItems.map((item, idx) => (
            <div key={idx} className="border p-4 rounded-lg shadow-md bg-background text-foreground">
              <div className="flex flex-col md:flex-row gap-6">
                <img 
                  src={item.mri_url} 
                  alt="MRI" 
                  className="w-full md:w-1/2 rounded-md object-cover"
                />
                <div className="flex flex-col justify-center w-full">
                  <p className="text-lg font-semibold mb-2">Timestamp: {item.timestamp}</p>
                  <p className="text-md">{item.summary}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs absolute bottom-2 right-2">Powered by NeuroAccess</p>
    </div>
  );
}
