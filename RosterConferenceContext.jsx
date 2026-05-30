import { createContext, useContext, useState } from "react";

const RosterConferenceContext = createContext(null);

export function RosterConferenceProvider({ children }) {
  const [conf, setConf] = useState("west");
  return (
    <RosterConferenceContext.Provider value={{ conf, setConf }}>
      {children}
    </RosterConferenceContext.Provider>
  );
}

export function useRosterConference() {
  const ctx = useContext(RosterConferenceContext);
  if (!ctx) {
    throw new Error("useRosterConference must be used within RosterConferenceProvider");
  }
  return ctx;
}
