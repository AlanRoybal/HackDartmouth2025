"use client";

export default function LoadingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground p-8">
      <h1 className="text-4xl font-bold mb-4">Processing your scan...</h1>
      <p className="text-lg mb-8">Please wait while we analyze your MRI image.</p>
      <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-primary" />
    </div>
  );
}
