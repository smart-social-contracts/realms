import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));

function loadLocale(name: string) {
  return JSON.parse(readFileSync(join(here, "i18n/locales", name), "utf-8"));
}

const LOCALES = ["en.json", "es.json", "de.json", "fr.json", "it.json", "zh-CN.json"];

describe("marketplace about copy", () => {
  for (const file of LOCALES) {
    it(`${file} recycles landing sections and drops hero chips`, () => {
      const loc = loadLocale(file);
      assert.equal(loc.landing.product_name, "Realms GOS");
      assert.ok(loc.landing.pitch);
      assert.ok(loc.landing.cta_about);
      assert.equal(loc.landing.badge_env, undefined);
      assert.equal(loc.landing.badge_version, undefined);
      assert.ok(loc.nav.about);
      assert.ok(loc.footer.build.includes("{version}"));
      assert.equal(loc.about.product_name, "Realms GOS");
      assert.ok(loc.about.hero.title);
      assert.ok(loc.about.mission.title);
      assert.ok(loc.about.principles.transparency.title);
      assert.ok(loc.about.features.internetComputer.title);
      assert.ok(loc.about.forPeople.identity.title);
      assert.ok(Array.isArray(loc.about.forPeople.identity.features));
      assert.ok(loc.about.forInstitutions.governments.title);
      assert.ok(Array.isArray(loc.about.forInstitutions.governments.benefits));
      assert.ok(loc.about.getStarted.demo.button);
    });
  }

  it("English about copy matches the website landing strings", () => {
    const about = loadLocale("en.json").about;
    const website = JSON.parse(
      readFileSync(join(here, "../../../../website/src/locales/en.json"), "utf-8"),
    );
    assert.equal(about.hero.title, website.hero.title);
    assert.equal(about.mission.description, website.mission.description);
    assert.equal(about.principles.transparency.description, website.principles.transparency.description);
    assert.equal(about.features.aiGovernors.description, website.features.aiGovernors.description);
    assert.deepEqual(about.forPeople.identity.features, website.forPeople.identity.features);
    assert.deepEqual(
      about.forInstitutions.governments.benefits,
      website.forInstitutions.governments.benefits,
    );
  });
});
