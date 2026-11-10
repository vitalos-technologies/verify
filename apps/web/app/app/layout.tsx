import Nav from "./Nav";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (<div className="console"><Nav />{children}</div>);
}
