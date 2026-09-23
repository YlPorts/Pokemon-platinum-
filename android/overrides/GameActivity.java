package org.pokeplatinum.android;

import android.content.pm.ActivityInfo;
import android.os.Bundle;
import org.libsdl.app.SDLActivity;

public final class GameActivity extends SDLActivity {
    @Override
    protected void onCreate(Bundle state) {
        int layout = getSharedPreferences("display_options", MODE_PRIVATE).getInt("layout", 0);
        setRequestedOrientation(layout == 0
                ? ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                : ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        super.onCreate(state);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Manifest runs this activity in :game. Dispose all native worker
        // threads and globals before another launch, leaving the launcher alive.
        if (!isChangingConfigurations()) android.os.Process.killProcess(android.os.Process.myPid());
    }
}
