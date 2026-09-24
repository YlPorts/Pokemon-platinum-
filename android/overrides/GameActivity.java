package org.pokeplatinum.android;

import android.content.pm.ActivityInfo;
import android.os.Bundle;
import org.libsdl.app.SDLActivity;

public final class GameActivity extends SDLActivity {
    @Override
    protected void onCreate(Bundle state) {
        int orientation = getIntent().getIntExtra("orientation", 0);
        setRequestedOrientation(orientation == 1 ? ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
                : orientation == 2 ? ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
                : ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR);
        super.onCreate(state);
    }

    @Override
    public void setOrientationBis(int width, int height, boolean resizable, String hint) {
        // SDL's initial DS window dimensions must not override the user's sensor mode.
        int orientation = getIntent().getIntExtra("orientation", 0);
        setRequestedOrientation(orientation == 1 ? ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
                : orientation == 2 ? ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
                : ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Manifest runs this activity in :game. Dispose all native worker
        // threads and globals before another launch, leaving the launcher alive.
        if (!isChangingConfigurations()) android.os.Process.killProcess(android.os.Process.myPid());
    }
}
