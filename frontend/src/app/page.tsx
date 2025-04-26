"use client";

import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  const handleClick = () => {
    router.push('/upload');
  };

  return (
    <div
      className="flex flex-col items-center justify-center h-screen bg-background text-foreground cursor-pointer"
      onClick={handleClick}
    >
      <h1 className="text-4xl font-bold mb-4">NeuroAccess</h1>
      <p className="text-lg mb-8">Neuro-oncology unlocked for anyone, everyone.</p>
      <p className="text-md accent"><i>Click to start</i></p>
    </div>
  );
}
