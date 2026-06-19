import { useEffect } from "react";
import { useRouter } from "next/router";
import { isAuthenticated, getCurrentUser } from "../lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    const { role } = getCurrentUser();
    router.replace(role === "DOCTOR" ? "/queue" : "/reception");
  }, [router]);

  return null;
}
