#!/usr/bin/env python3
from final_project.migrations.add_has_temp_password import migrate

if __name__ == "__main__":
    print("Running database migration...")
    migrate()
    print("Migration completed")

