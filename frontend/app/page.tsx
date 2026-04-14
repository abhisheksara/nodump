import FeedList from "@/components/FeedList";
import ChatPanel from "@/components/ChatPanel";

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-baseline justify-between">
          <div>
            <h1 className="text-base font-bold text-zinc-100 tracking-tight">
              AI Research Feed
            </h1>
            <p className="text-xs text-zinc-600 mt-0.5">
              5 things in AI today — curated and explained for you
            </p>
          </div>
          <span className="text-xs text-zinc-700">
            {new Date().toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>
      </header>

      {/* Main layout */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">
          {/* Feed */}
          <section>
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-4">
              Today&apos;s Feed
            </h2>
            <FeedList />
          </section>

          {/* Chat sidebar */}
          <aside>
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-4">
              Ask Your Feed
            </h2>
            <div className="border border-zinc-800 rounded-lg p-4 sticky top-6">
              <ChatPanel />
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
