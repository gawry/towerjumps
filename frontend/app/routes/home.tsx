import type { Route } from "./+types/home";
import { TowerJumpsAnalyzer } from "../components/TowerJumpsAnalyzer";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "🗼 Tower Jumps Analysis" },
    { name: "description", content: "Analyze mobile carrier data to detect tower jumps with real-time streaming" },
  ];
}

export default function Home() {
  return <TowerJumpsAnalyzer />;
}
