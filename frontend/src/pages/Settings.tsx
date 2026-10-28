import { Link } from "react-router";
import { Card } from "../components/Card";
import { useSettings } from "../api/hooks";
import { AccountCard } from "./settings/AccountCard";
import { DiscordCard } from "./settings/DiscordCard";
import { RegionCard } from "./settings/RegionCard";
import { TokensCard } from "./settings/TokensCard";

export function Settings() {
  const settings = useSettings();
  if (settings.isError) return <p className="error">Couldn't load settings.</p>;
  if (!settings.data) return null;
  return (
    <div className="records settings">
      <h1>Settings</h1>
      <RegionCard settings={settings.data} />
      <DiscordCard isSet={settings.data.discord_webhook_set} />
      <TokensCard s={settings.data} />
      <Card label="Import">
        <p>
          Moving from LubeLogger? <Link to="/settings/import">Import from LubeLogger</Link>
        </p>
      </Card>
      <AccountCard />
    </div>
  );
}
