import com.android.apksig.ApkSigner;
import java.io.File;
import java.io.FileInputStream;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import java.util.Collections;

/* Signs an APK (v2 scheme; minSdk 24 needs no v1) with a key from a PKCS12 keystore: Sign <keystore> <alias> <password> <in.apk> <out.apk> */
public class Sign {
    public static void main(String[] a) throws Exception {
        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (FileInputStream in = new FileInputStream(a[0])) { ks.load(in, a[2].toCharArray()); }
        PrivateKey key = (PrivateKey) ks.getKey(a[1], a[2].toCharArray());
        X509Certificate cert = (X509Certificate) ks.getCertificate(a[1]);
        ApkSigner.SignerConfig cfg = new ApkSigner.SignerConfig.Builder("launchpad", key, Collections.singletonList(cert)).build();
        new ApkSigner.Builder(Collections.singletonList(cfg))
                .setInputApk(new File(a[3])).setOutputApk(new File(a[4]))
                .setMinSdkVersion(24).setV1SigningEnabled(false).setV2SigningEnabled(true)
                .build().sign();
    }
}
