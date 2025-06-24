# Creating Tortoise migrations

* Make sure your branch is on head.
* Make a change to the model file you want to change.
* Find the aerich executable (should be in laserforce_ranking/Scripts if you're using Windows).
* Double-check that you're up-to-date with migrations:
  `laserforce_ranking/Scripts/aerich.exe heads`
* If it shows any migrations, you'll need to run them first:
  `laserforce_ranking/Scripts/aerich.exe upgrade`
* If you don't do that, creating a new migration is going to clash with existing ones and you're
  going to regret this.
* If you try it and it fails because it tries to apply migrations that you already have in your
  local schema, you can locally change the patch files to have an empty upgrade query, for example
  `SELECT TRUE;`. I'm sure there's a proper way to skip a migration but I don't know it, and who
  cares about reading documentation when you can just hack it instead.
* Run `laserforce_ranking/Scripts/aerich.exe migrate --name <name_for_this_schema_change>`.
* This will generate the patch file. Make that part of your CL.
* Now run `laserforce_ranking/Scripts/aerich.exe upgrade` to apply it.
* Your database is updated. Congrats.
