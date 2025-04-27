"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from "next/navigation";
import { Spacer } from "@/components/ui/spacer";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import Image from "next/image";

// Define types for our history items
interface HistoryItemType {
  id: string;
  image_url: string;
  summary: string;
  timestamp: string;
  json_url: string;
  full_data: Record<string, any>;
}

interface HistoryItemProps {
  item: HistoryItemType;
}

function HistoryItem({ item }: HistoryItemProps) {
  const [viewDetails, setViewDetails] = useState(false);

  return (
    <Card className="p-6 hover:shadow-md transition-shadow">
      <div className="flex flex-col md:flex-row gap-6">
        <div className="relative h-48 w-48 overflow-hidden rounded-md shrink-0">
          <Image
            src={item.image_url}
            alt="MRI Scan"
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 192px"
          />
        </div>

        <div className="flex-1 flex flex-col">
          <span className="text-sm text-muted-foreground mb-2">
            {item.timestamp}
          </span>
          <div className="mb-4 flex-grow">
            <p>{item.summary}</p>
          </div>

          {viewDetails && (
            <div className="mt-4 p-4 bg-muted rounded-md">
              <h4 className="font-medium mb-2">Detailed Analysis</h4>
              <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(item.full_data, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex gap-2 mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewDetails(!viewDetails)}
            >
              {viewDetails ? "Hide Details" : "View Details"}
            </Button>
            <Button variant="secondary" size="sm" asChild>
              <Link
                href={item.json_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Download Results
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function HistoryPage() {
  const router = useRouter();
  const [historyItems, setHistoryItems] = useState<HistoryItemType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/get_history`
        );

        if (!response.ok) {
          throw new Error(`Error fetching history: ${response.statusText}`);
        }

        const data = await response.json();
        setHistoryItems(data.items || []);
      } catch (err) {
        console.error("Failed to fetch history:", err);
        setError(
          err instanceof Error ? err.message : "An unknown error occurred"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="flex flex-col items-center justify-start min-h-screen bg-background text-foreground p-8 relative">
      <Tabs
        defaultValue="history"
        className="w-full max-w-4xl mb-8"
        onValueChange={(value) => {
          if (value === "upload") router.push("/upload");
        }}
      >
        <TabsList>
          <TabsTrigger value="history">View History</TabsTrigger>
          <TabsTrigger value="upload">Upload Images</TabsTrigger>
        </TabsList>
      </Tabs>

      <Spacer axis="vertical" size={20} />

      <h1 className="text-4xl font-bold mb-4">MRI Analysis History</h1>
      <p className="text-lg mb-8">
        View your previous MRI scan analyses and results.
      </p>

      {loading ? (
        <div className="w-full max-w-4xl space-y-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <div className="flex flex-col md:flex-row gap-6">
                <Skeleton className="h-48 w-48 rounded-md" />
                <div className="flex-1 space-y-4">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-10 w-32" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : error ? (
        <div className="text-center p-8 border border-destructive rounded-lg">
          <p className="text-destructive mb-4">
            Error loading history: {error}
          </p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </div>
      ) : historyItems.length === 0 ? (
        <div className="text-center p-8 border border-border rounded-lg w-full max-w-4xl">
          <p className="mb-4">No history available yet.</p>
          <Button onClick={() => router.push("/upload")}>
            Upload an MRI Scan
          </Button>
        </div>
      ) : (
        <div className="w-full max-w-4xl space-y-6">
          {historyItems.map((item) => (
            <HistoryItem key={item.id} item={item} />
          ))}
        </div>
      )}

      <p className="text-xs absolute bottom-2 right-2">
        Powered by NeuroAccess
      </p>
    </div>
  );
}
