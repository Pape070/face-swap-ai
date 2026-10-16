package com.headswap.studio

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.LinearLayout
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity

/**
 * HeadSwap Studio — Android edition.
 *
 * A thin native shell around the HeadSwap web app: enter the server URL
 * (your computer running `python app.py`, or a hosted instance), then use
 * the full uploader / sliders / progress / result flow inside the WebView.
 * File picking (photo + video) is wired through onShowFileChooser.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null

    private val filePicker =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val uris = if (result.resultCode == Activity.RESULT_OK) {
                val data: Intent? = result.data
                when {
                    data?.clipData != null -> Array(data.clipData!!.itemCount) {
                        data.clipData!!.getItemAt(it).uri
                    }
                    data?.data != null -> arrayOf(data.data!!)
                    else -> null
                }
            } else null
            filePathCallback?.onReceiveValue(uris)
            filePathCallback = null
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }
        webView = WebView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
            )
        }
        root.addView(webView)
        setContentView(root)
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = true
            cacheMode = WebSettings.LOAD_DEFAULT
        }
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                view: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                params: FileChooserParams?
            ): Boolean {
                filePathCallback?.onReceiveValue(null)
                filePathCallback = callback
                return try {
                    val intent = params?.createIntent()
                        ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "*/*"
                            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/*", "video/*"))
                        }
                    filePicker.launch(intent)
                    true
                } catch (_: Exception) {
                    filePathCallback = null
                    false
                }
            }
        }
        val prefs = getPreferences(MODE_PRIVATE)
        val lastUrl = prefs.getString(KEY_URL, DEFAULT_URL) ?: DEFAULT_URL
        if (savedInstanceState == null && lastUrl.isBlank()) {
            askForServerUrl("")
        } else {
            webView.loadUrl(if (lastUrl.isBlank()) DEFAULT_URL else lastUrl)
        }
    }

    private fun askForServerUrl(current: String) {
        val input = EditText(this).apply {
            setText(current)
            hint = DEFAULT_URL
        }
        AlertDialog.Builder(this)
            .setTitle("HeadSwap server URL")
            .setMessage("Enter the address of your HeadSwap server, e.g. http://192.168.1.5:3000")
            .setView(input)
            .setPositiveButton("Connect") { _, _ ->
                val url = input.text.toString().trim().ifBlank { DEFAULT_URL }
                getPreferences(MODE_PRIVATE).edit().putString(KEY_URL, url).apply()
                webView.loadUrl(url)
            }
            .setCancelable(false)
            .show()
    }

    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }

    override fun onDestroy() {
        filePathCallback?.onReceiveValue(null)
        filePathCallback = null
        super.onDestroy()
    }

    companion object {
        private const val KEY_URL = "server_url"
        private const val DEFAULT_URL = "http://10.0.2.2:3000"
    }
}
