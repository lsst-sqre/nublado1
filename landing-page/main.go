// A tiny web server that serves a directory's contents
package main

import (
	"fmt"
	"net/http"
	"os"
)

func get_with_default(envstr, def string) string {
	t := os.Getenv(envstr)
	if t != "" {
		return t
	}
	return def
}

func main() {
	port := get_with_default("HTTP_PORT","8080")
	content_dir := get_with_default("HTTP_CONTENT_DIR","/www")
	fs := http.StripPrefix("/", http.FileServer(http.Dir(content_dir)))
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fs.ServeHTTP(w, r)
	})
	fmt.Println("Server started on port " + port + ".")
	err := http.ListenAndServe(":" + port, nil)
	if err != nil {
		panic("ListenAndServe: " + err.Error())
	}
	select {}
}

